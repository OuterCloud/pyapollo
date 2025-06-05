"""
Apollo Python client implementation.

This is a rewritten version of the Apollo Python client SDK based on:
- Original SDK by filamoon (https://github.com/filamoon/pyapollo)
- Updated SDK by BruceWW (https://github.com/BruceWW/pyapollo)

Key improvements:
- Fixed long polling issues
- Updated API endpoints
- Removed deprecated telnetlib usage for Python 3.13+ compatibility
- Added app secret support
- Thread-safe improvements
- Added pydantic-settings support for configuration

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
import threading
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Union

import requests
from loguru import logger

from pyapollo.exceptions import ServerNotResponseException
from pyapollo.interface import ConfigClientInterface
from pyapollo.settings import ApolloSettingsConfig


class ApolloClient(ConfigClientInterface):
    """Apollo client based on the official HTTP API"""

    _instances = {}
    _create_client_lock = threading.Lock()
    _update_cache_lock = threading.Lock()
    _cache_file_write_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        key = f"{args},{sorted(kwargs.items())}"
        with cls._create_client_lock:
            if key not in cls._instances:
                cls._instances[key] = super().__new__(cls)
        return cls._instances[key]

    def __init__(
        self,
        meta_server_address: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        cluster: str = "default",
        env: str = "DEV",
        namespaces: List[str] = ["application"],
        ip: Optional[str] = None,
        timeout: int = 10,
        cycle_time: int = 30,
        cache_file_dir_path: Optional[str] = None,
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
            timeout: HTTP request timeout seconds, default value is 60 seconds
            ip: Deploy IP for grey release, default value is the local IP
            cycle_time: Cycle time to update configuration content from server
            cache_file_dir_path: Directory path to store the configuration cache file
            settings: ApolloSettingsConfig instance, if provided other parameters will be ignored

        You can initialize the client in three ways:
        1. Using environment variables (requires no parameters):
            ```python
            client = ApolloClient()  # Will use environment variables with APOLLO_ prefix
            ```

        2. Using ApolloSettingsConfig:
            ```python
            settings = ApolloSettingsConfig(
                meta_server_address="http://localhost:8080",
                app_id="my-app"
            )
            client = ApolloClient(settings=settings)
            ```

        3. Using direct parameters:
            ```python
            client = ApolloClient(
                meta_server_address="http://localhost:8080",
                app_id="my-app"
            )
            ```
        """
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
            self._notification_map = {
                namespace: -1 for namespace in settings.namespaces
            }
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
            self._notification_map = {namespace: -1 for namespace in namespaces}

        # Initialize other attributes
        self._cache: Dict = {}
        self._hash: Dict = {}
        self._config_server_url = None
        self._config_server_host = None
        self._config_server_port = None

        # Initialize cache directory path
        self._init_cache_file_dir_path(self._cache_file_dir_path)

        # Start client
        self.update_config_server()
        self.fetch_configuration()
        self.start_polling_thread()

    def _update_config_server_host_port(self):
        """
        Initialize the config server host and port
        """

        remote = self._config_server_url.split(":")
        self._config_server_host = f"{remote[0]}:{remote[1]}"
        if len(remote) == 1:
            self._config_server_port = 8090
        else:
            self._config_server_port = int(remote[2].rstrip("/"))

    def _init_cache_file_dir_path(self, cache_file_dir_path):
        """
        Initialize the cache file directory path
        :param cache_file_dir_path: the cache file directory path
        """

        if cache_file_dir_path is None:
            self._cache_file_dir_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "config"
            )
        else:
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

    def _listener(self) -> None:
        """
        Long polling loop to get configuration from apollo server
        """

        while not self._stop_event.is_set():
            self.fetch_configuration()
            self._stop_event.wait(self._cycle_time)

    def start_polling_thread(self) -> None:
        """
        Start the long polling loop thread
        """

        self._stop_event = threading.Event()
        t = threading.Thread(target=self._listener)
        t.daemon = True
        t.start()
        logger.success("Apollo polling thread started")

    def stop_polling_thread(self) -> None:
        """
        Stop the long polling loop thread
        """

        self._stop_event.set()
        logger.success("Apollo polling thread stopped")

    def update_local_file_cache(
        self, release_key: str, data: str, namespace: str = "application"
    ) -> None:
        """
        Update local cache file if the release key is updated
        """

        if self._hash.get(namespace) != release_key:
            with self._cache_file_write_lock:
                _cache_file_path = os.path.join(
                    self._cache_file_dir_path,
                    f"{self._app_id}_configuration_{namespace}.txt",
                )
                with open(_cache_file_path, "w", encoding="utf-8") as f:
                    new_string = json.dumps(data)
                    f.write(new_string)
                self._hash[namespace] = release_key

    def get_local_file_cache(self, namespace: str = "application") -> Dict:
        """
        Get configuration from local cache file
        """

        cache_file_path = os.path.join(
            self._cache_file_dir_path, f"{self._app_id}_configuration_{namespace}.txt"
        )
        try:
            with open(cache_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error reading cache file {cache_file_path}: {e}")
            return {}

    def _http_get(self, url: str, params: Dict = None) -> requests.Response:
        try:
            headers = (
                self._build_http_headers(url, self._app_id, self._app_secret)
                if self._app_secret
                else {}
            )
            return requests.get(
                url=url, params=params, timeout=self._timeout, headers=headers
            )
        except requests.exceptions.Timeout:
            raise ServerNotResponseException(f"Request to {url} timed out.")
        except requests.exceptions.ConnectionError:
            raise ServerNotResponseException(f"Failed to connect to {url}.")

    def update_cache(self, namespace, data):
        """
        Update cache
        """

        with self._update_cache_lock:
            self._cache[namespace] = data

    def fetch_config_by_namespace(self, namespace: str = "application") -> None:
        """
        Fetch configuration of the namespace from apollo server
        """

        url = f"{self._config_server_host}:{self._config_server_port}/configs/{self._app_id}/{self._cluster}/{namespace}"
        try:
            r = self._http_get(url)
            if r.status_code == 200:
                data = r.json()
                configurations = data.get("configurations", {})
                release_key = data.get("releaseKey", str(time.time()))
                self.update_cache(namespace, configurations)

                self.update_local_file_cache(
                    release_key=release_key,
                    data=configurations,
                    namespace=namespace,
                )
            else:
                logger.warning(
                    "Get configuration from apollo failed, load from local cache file"
                )
                data = self.get_local_file_cache(namespace)
                self.update_cache(namespace, data)

        except Exception as e:
            data = self.get_local_file_cache(namespace)
            self.update_cache(namespace, data)

            logger.error(
                f"Fetch apollo configuration meet error, error: {e}, url: {url}, config server url: {self._config_server_url}, host: {self._config_server_host}, port: {self._config_server_port}"
            )
            self.update_config_server(exclude=self._config_server_host)

    def fetch_configuration(self) -> None:
        """
        Get configurations for all namespaces from apollo server
        """

        try:
            for namespace in self._notification_map.keys():
                self.fetch_config_by_namespace(namespace)
        except requests.exceptions.ReadTimeout as e:
            logger.warning(str(e))
        except requests.exceptions.ConnectionError as e:
            logger.warning(str(e))
            self.load_local_cache_file()

    def load_local_cache_file(self) -> bool:
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
                    with open(file_path) as f:
                        data = json.loads(f.read())
                        self.update_cache(namespace, data)
            return True
        except Exception as e:
            logger.error(f"Error loading local cache files: {e}")
            return False

    def get_service_conf(self) -> List:
        """
        Get the config servers

        """
        service_conf_url = f"{self._meta_server_address}/services/config"
        service_conf: list = requests.get(service_conf_url).json()
        if not service_conf:
            raise ValueError("No apollo service found")
        return service_conf

    def update_config_server(self, exclude: str = None) -> str:
        """
        Update the config server info
        """

        service_conf = self.get_service_conf()
        logger.debug(f"Apollo service conf: {service_conf}")
        if exclude:
            service_conf = [
                service for service in service_conf if service["homepageUrl"] != exclude
            ]
        service = service_conf[0]
        self._config_server_url = service["homepageUrl"]

        remote = self._config_server_url.split(":")
        self._config_server_host = f"{remote[0]}:{remote[1]}"
        if len(remote) == 1:
            self._config_server_port = 8090
        else:
            self._config_server_port = int(remote[2].rstrip("/"))

        logger.info(
            f"Update config server url to: {self._config_server_url}, host: {self._config_server_host}, port: {self._config_server_port}"
        )

        return self._config_server_url

    def get_value(
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

    def get_json_value(
        self,
        key: str,
        default_val: Union[dict, None] = None,
        namespace: str = "application",
    ) -> Any:
        """
        Get the configuration value and convert it to json format
        """

        val = self.get_value(key, namespace=namespace)
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            logger.error(f"The value of key({key}) is not json format")

        return default_val or {}
