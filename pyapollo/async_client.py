"""
Asynchronous Apollo Python client implementation.

This is an asynchronous version of the Apollo Python client SDK.
It supports Python 3.7 to 3.13 and uses aiohttp for HTTP requests.

Key features:
- Fully asynchronous API
- Compatible with Python 3.7 to 3.13
- Thread-safe with asyncio locks
- Supports async context manager
- Implements Apollo's official HTTP API
- Supports configuration via environment variables and .env files

Implements Apollo's official HTTP API:
English: https://www.apolloconfig.com/#/en/client/other-language-client-user-guide
中文: https://www.apolloconfig.com/#/zh/client/other-language-client-user-guide
"""

import os
import json
import time
import hmac
import socket
import base64
import hashlib
import asyncio
import sys
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

import aiohttp
import aiofiles
from loguru import logger

from pyapollo.exceptions import ServerNotResponseException
from pyapollo.async_interface import AsyncConfigClientInterface
from pyapollo.settings import ApolloSettingsConfig


class AsyncApolloClient(AsyncConfigClientInterface):
    """Asynchronous Apollo client based on the official HTTP API"""

    _instances = {}
    _instance_lock = None  # Will be initialized in __new__

    def __new__(cls, *args, **kwargs):
        # Initialize class lock if not already initialized
        if cls._instance_lock is None:
            cls._instance_lock = asyncio.Lock()

        # We can't use async/await in __new__, so we'll initialize the instance
        # and set up the singleton pattern in __init__
        instance = super().__new__(cls)
        instance._initialized = False
        return instance

    def __init__(
        self,
        meta_server_address: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        cluster: str = "default",
        env: str = "DEV",
        namespaces: Optional[List[str]] = None,
        ip: Optional[str] = None,
        timeout: int = 10,
        cycle_time: int = 30,
        cache_file_dir_path: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
        settings: Optional[ApolloSettingsConfig] = None,
    ):
        """
        Initialize method

        Args:
            meta_server_address: Apollo meta server address, format is like 'https://xxx/yyy'
            app_id: Application ID
            app_secret: Application secret, optional
            cluster: Cluster name, default value is 'default'
            env: Environment, default value is 'DEV'
            namespaces: Namespace list to get configuration, default value is ['application']
            timeout: HTTP request timeout seconds, default value is 10 seconds
            ip: Deploy IP for grey release, default value is the local IP
            cycle_time: Cycle time to update configuration content from server
            cache_file_dir_path: Directory path to store the configuration cache file
            session: aiohttp client session, if not provided, a new one will be created
            settings: ApolloSettingsConfig instance, if provided other parameters will be ignored

        You can initialize the client in three ways:
        1. Using environment variables (requires no parameters):
            ```python
            client = AsyncApolloClient()  # Will use environment variables with APOLLO_ prefix
            ```

        2. Using ApolloSettingsConfig:
            ```python
            settings = ApolloSettingsConfig(
                meta_server_address="http://localhost:8080",
                app_id="my-app"
            )
            client = AsyncApolloClient(settings=settings)
            ```

        3. Using direct parameters:
            ```python
            client = AsyncApolloClient(
                meta_server_address="http://localhost:8080",
                app_id="my-app"
            )
            ```
        """
        # Skip initialization if already initialized (singleton pattern)
        if hasattr(self, "_initialized") and self._initialized:
            return

        # Load configuration from settings or environment if no direct parameters provided
        if settings is None and meta_server_address is None and app_id is None:
            settings = ApolloSettingsConfig()  # Will load from environment variables

        # Initialize cache directory path first
        self._cache_file_dir_path = None

        # If settings is provided, use it
        if settings is not None:
            self._meta_server_address = settings.meta_server_address
            self._app_id = settings.app_id
            self._app_secret = (
                settings.app_secret if settings.using_app_secret else None
            )
            self._cluster = settings.cluster
            self._timeout = settings.timeout
            self._env = settings.env
            self._cycle_time = settings.cycle_time
            self._cache_file_dir_path = settings.cache_file_dir_path
            self.ip = self._get_local_ip_address(settings.ip)
            namespaces = settings.namespaces
        else:
            # Use direct parameters
            self._meta_server_address = meta_server_address
            self._app_id = app_id
            self._app_secret = app_secret
            self._cluster = cluster
            self._timeout = timeout
            self._env = env
            self._cycle_time = cycle_time
            self._cache_file_dir_path = cache_file_dir_path
            self.ip = self._get_local_ip_address(ip)
            if namespaces is None:
                namespaces = ["application"]

        # Initialize notification map
        self._notification_map = {namespace: -1 for namespace in namespaces}

        # Initialize other attributes
        self._cache: Dict = {}
        self._hash: Dict = {}
        self._config_server_url = None
        self._config_server_host = None
        self._config_server_port = None

        # Initialize cache directory path if not set
        self._init_cache_file_dir_path(self._cache_file_dir_path)

        # Asyncio specific attributes
        self._update_cache_lock = asyncio.Lock()
        self._cache_file_write_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._polling_task = None
        self._session = session
        self._owns_session = session is None  # Track if we created the session
        self._initialized = True

        # Store instance in class dictionary for singleton pattern
        key = f"{self._meta_server_address},{self._app_id},{self._cluster},{self._env},{tuple(namespaces)}"
        AsyncApolloClient._instances[key] = self

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        await self.update_config_server()
        await self.fetch_configuration()
        await self.start_polling()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop_polling()
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    def _init_cache_file_dir_path(self, cache_file_dir_path=None):
        """
        Initialize the cache file directory path
        :param cache_file_dir_path: the cache file directory path
        """
        if cache_file_dir_path is None and self._cache_file_dir_path is None:
            self._cache_file_dir_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "config"
            )
        elif cache_file_dir_path is not None:
            self._cache_file_dir_path = cache_file_dir_path

        # Ensure the cache directory exists
        if not os.path.isdir(self._cache_file_dir_path):
            os.makedirs(self._cache_file_dir_path, exist_ok=True)

    @staticmethod
    def _sign_string(string_to_sign: str, secret: str) -> str:
        """
        Sign the string with the secret
        """
        signature = hmac.new(
            secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def _url_to_path_with_query(url: str) -> str:
        """
        Convert the url to path with query
        """
        parsed = urlparse(url)
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return path + query

    def _build_http_headers(self, url: str, app_id: str, secret: str) -> Dict[str, str]:
        """
        Build the http headers
        """
        timestamp = str(int(time.time() * 1000))
        path_with_query = self._url_to_path_with_query(url)
        string_to_sign = f"{timestamp}\n{path_with_query}"
        signature = self._sign_string(string_to_sign, secret)

        AUTHORIZATION_FORMAT = "Apollo {}:{}"
        HTTP_HEADER_AUTHORIZATION = "Authorization"
        HTTP_HEADER_TIMESTAMP = "Timestamp"

        return {
            HTTP_HEADER_AUTHORIZATION: AUTHORIZATION_FORMAT.format(app_id, signature),
            HTTP_HEADER_TIMESTAMP: timestamp,
        }

    @staticmethod
    def _get_local_ip_address(ip: Optional[str]) -> str:
        """
        Get the local ip address
        """
        if ip is None:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                ip = s.getsockname()[0]
                s.close()
            except BaseException:
                return "127.0.0.1"
        return ip

    async def _listener(self) -> None:
        """
        Asynchronous polling loop to get configuration from apollo server
        """
        while not self._stop_event.is_set():
            try:
                await self.fetch_configuration()
                # Use asyncio.wait_for with a timeout
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._cycle_time
                    )
                except asyncio.TimeoutError:
                    # This is expected when the timeout is reached
                    pass
            except Exception as e:
                logger.error(f"Error in Apollo polling loop: {e}")
                # Wait a bit before retrying to avoid tight loop on persistent errors
                await asyncio.sleep(1)

    async def start_polling(self) -> None:
        """
        Start the asynchronous polling task
        """
        if self._polling_task is not None:
            return  # Already polling

        self._stop_event.clear()

        # Get the appropriate event loop based on Python version
        try:
            loop = asyncio.get_running_loop()
        except AttributeError:  # Python 3.7 doesn't have get_running_loop
            loop = asyncio.get_event_loop()

        self._polling_task = loop.create_task(self._listener())
        logger.success("Apollo async polling task started")

    async def stop_polling(self) -> None:
        """
        Stop the asynchronous polling task
        """
        if self._polling_task is None:
            return  # Not polling

        self._stop_event.set()

        if self._polling_task is not None:
            try:
                # Wait for the task to complete with a timeout
                await asyncio.wait_for(self._polling_task, timeout=2)
            except asyncio.TimeoutError:
                # If the task doesn't complete in time, cancel it
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                logger.error(f"Error stopping Apollo polling task: {e}")
            finally:
                self._polling_task = None

        logger.success("Apollo async polling task stopped")

    async def update_local_file_cache(
        self, release_key: str, data: Any, namespace: str = "application"
    ) -> None:
        """
        Update local cache file if the release key is updated
        """
        if self._hash.get(namespace) != release_key:
            async with self._cache_file_write_lock:
                _cache_file_path = os.path.join(
                    self._cache_file_dir_path,
                    f"{self._app_id}_configuration_{namespace}.txt",
                )
                # Use async file operations if available, otherwise fall back to sync
                try:
                    async with aiofiles.open(
                        _cache_file_path, "w", encoding="utf-8"
                    ) as f:
                        new_string = json.dumps(data)
                        await f.write(new_string)
                except ImportError:
                    # Fall back to synchronous file operations
                    with open(_cache_file_path, "w", encoding="utf-8") as f:
                        new_string = json.dumps(data)
                        f.write(new_string)

                self._hash[namespace] = release_key

    async def get_local_file_cache(self, namespace: str = "application") -> Dict:
        """
        Get configuration from local cache file
        """
        cache_file_path = os.path.join(
            self._cache_file_dir_path, f"{self._app_id}_configuration_{namespace}.txt"
        )
        try:
            # Use async file operations if available, otherwise fall back to sync
            try:
                async with aiofiles.open(cache_file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content)
            except ImportError:
                # Fall back to synchronous file operations
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    return json.loads(f.read())
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading cache file {cache_file_path}: {e}")
            return {}

    async def _http_get(self, url: str, params: Dict = None) -> Dict:
        """
        Perform asynchronous HTTP GET request
        """
        await self._ensure_session()

        headers = (
            self._build_http_headers(url, self._app_id, self._app_secret)
            if self._app_secret
            else {}
        )

        try:
            async with self._session.get(
                url=url, params=params, timeout=self._timeout, headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    logger.warning(
                        f"HTTP request failed with status {response.status}: {text}"
                    )
                    return {}
        except asyncio.TimeoutError:
            raise ServerNotResponseException(f"Request to {url} timed out.")
        except aiohttp.ClientConnectionError:
            raise ServerNotResponseException(f"Failed to connect to {url}.")

    async def update_cache(self, namespace: str, data: Dict) -> None:
        """
        Update in-memory configuration cache
        """
        async with self._update_cache_lock:
            self._cache[namespace] = data

    async def fetch_config_by_namespace(self, namespace: str = "application") -> None:
        """
        Fetch configuration of the namespace from apollo server
        """
        url = f"{self._config_server_host}:{self._config_server_port}/configs/{self._app_id}/{self._cluster}/{namespace}"
        try:
            data = await self._http_get(url)
            if data:
                configurations = data.get("configurations", {})
                release_key = data.get("releaseKey", str(time.time()))
                await self.update_cache(namespace, configurations)

                await self.update_local_file_cache(
                    release_key=release_key,
                    data=configurations,
                    namespace=namespace,
                )
            else:
                logger.warning(
                    "Get configuration from apollo failed, load from local cache file"
                )
                data = await self.get_local_file_cache(namespace)
                await self.update_cache(namespace, data)

        except Exception as e:
            data = await self.get_local_file_cache(namespace)
            await self.update_cache(namespace, data)

            logger.error(
                f"Fetch apollo configuration meet error, error: {e}, url: {url}, "
                f"config server url: {self._config_server_url}, host: {self._config_server_host}, "
                f"port: {self._config_server_port}"
            )
            await self.update_config_server(exclude=self._config_server_host)

    async def fetch_configuration(self) -> None:
        """
        Get configurations for all namespaces from apollo server
        """
        try:
            for namespace in self._notification_map.keys():
                await self.fetch_config_by_namespace(namespace)
        except aiohttp.ClientError as e:
            logger.warning(f"HTTP client error: {str(e)}")
            await self.load_local_cache_file()
        except asyncio.TimeoutError as e:
            logger.warning(f"Request timeout: {str(e)}")
            await self.load_local_cache_file()

    async def load_local_cache_file(self) -> bool:
        """
        Load local cache file to memory
        """
        try:
            for file_name in os.listdir(self._cache_file_dir_path):
                file_path = os.path.join(self._cache_file_dir_path, file_name)
                if os.path.isfile(file_path):
                    file_simple_name, file_ext_name = os.path.splitext(file_name)
                    if file_ext_name == ".swp":
                        continue
                    if not file_simple_name.startswith(
                        f"{self._app_id}_configuration_"
                    ):
                        continue

                    namespace = file_simple_name.split("_")[-1]

                    # Use async file operations if available, otherwise fall back to sync
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                            content = await f.read()
                            data = json.loads(content)
                    except ImportError:
                        # Fall back to synchronous file operations
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.loads(f.read())

                    await self.update_cache(namespace, data)
            return True
        except Exception as e:
            logger.error(f"Error loading local cache files: {e}")
            return False

    async def get_service_conf(self) -> List:
        """
        Get the config servers
        """
        await self._ensure_session()
        service_conf_url = f"{self._meta_server_address}/services/config"

        try:
            async with self._session.get(service_conf_url) as response:
                if response.status == 200:
                    service_conf = await response.json()
                    if not service_conf:
                        raise ValueError("No apollo service found")
                    return service_conf
                else:
                    text = await response.text()
                    raise ValueError(
                        f"Failed to get service config: {response.status} - {text}"
                    )
        except Exception as e:
            logger.error(f"Error getting service configuration: {e}")
            raise

    async def update_config_server(self, exclude: str = None) -> str:
        """
        Update the config server info
        """
        service_conf = await self.get_service_conf()
        logger.debug(f"Apollo service conf: {service_conf}")

        if exclude:
            service_conf = [
                service for service in service_conf if service["homepageUrl"] != exclude
            ]

        if not service_conf:
            raise ValueError("No available config server")

        service = service_conf[0]
        self._config_server_url = service["homepageUrl"]

        # Parse the URL to get host and port
        remote = self._config_server_url.split(":")
        self._config_server_host = f"{remote[0]}:{remote[1]}"
        if len(remote) == 1:
            self._config_server_port = 8090
        else:
            self._config_server_port = int(remote[2].rstrip("/"))

        logger.info(
            f"Update config server url to: {self._config_server_url}, "
            f"host: {self._config_server_host}, port: {self._config_server_port}"
        )

        return self._config_server_url

    async def get_value(
        self, key: str, default_val: str = None, namespace: str = "application"
    ) -> Any:
        """
        Get the configuration value
        """
        try:
            if namespace in self._cache:
                return self._cache[namespace].get(key, default_val)
            return default_val
        except Exception as e:
            logger.error(f"Get key({key}) value failed, error: {e}")
            return default_val

    async def get_json_value(self, key: str, namespace: str = "application") -> Any:
        """
        Get the configuration value and convert it to json format
        """
        val = await self.get_value(key, namespace=namespace)
        if val is None:
            return {}

        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            logger.error(f"The value of key({key}) is not json format")
            return {}
