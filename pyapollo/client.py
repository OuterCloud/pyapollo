"""
The first version SDK: https://github.com/filamoon/pyapollo
Will cause an error while long polling

The second version SDK: https://github.com/BruceWW/pyapollo
The urls maybe outdated and return 404 now
And the telnetlib module used in the SDK has been deprecated in Python 3.13

Base on above, I rewrite the SDK to support the new apollo server based on the BruceWW's SDK
Also based on the official http api document:
https://www.apolloconfig.com/#/zh/client/other-language-client-user-guide
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
from typing import Any, Dict, List, Optional

import requests
from loguru import logger


class BasicException(BaseException):
    def __init__(self, msg: str):
        self._msg = msg


class NameSpaceNotFoundException(BasicException):
    pass


class ServerNotResponseException(BasicException):
    pass


class ApolloClient(object):
    """Apollo client based on the official HTTP API"""

    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern
        """
        tmp = {_: kwargs[_] for _ in sorted(kwargs)}
        key = f"{args},{tmp}"
        if hasattr(cls, "_instance"):
            if key not in cls._instance:
                cls._instance[key] = super().__new__(cls)
        else:
            cls._instance = {key: super().__new__(cls)}
        return cls._instance[key]

    def __init__(
        self,
        meta_server_address: str,
        app_id: str,
        app_secret: str = None,
        cluster: str = "default",
        env: str = "DEV",
        namespaces: List[str] = ["application"],
        ip: str = None,
        timeout: int = 60,
        cycle_time: int = 30,
        cache_file_path: str = None,
    ):
        """
        Initialize method

        :param meta_server_address: the meta server address, format is like 'https://xxx/yyy'
        :param app_id: application id
        :param app_secret: application secret, optional
        :param cluster: cluster name, default value is 'default'
        :param env: environment, default value is 'DEV'
        :param namespaces: the namespace list to get configuration, default value is ['application']
        :param timeout: http request timeout seconds, default value is 60 seconds
        :param ip: the deploy ip for grey release, default value is the local ip
        :param cycle_time: the cycle time to update configuration content from server
        :param cache_file_path: local cache file store path
        """

        self._meta_server_address = meta_server_address
        self._app_id = app_id
        self._app_secret = app_secret
        self._cluster = cluster
        self._timeout = timeout
        self._env = env
        self._cache: Dict = {}
        self._notification_map = {namespace: -1 for namespace in namespaces}
        self._cycle_time = cycle_time
        self._hash: Dict = {}
        self._config_server_url = None
        self._config_server_host = None
        self._config_server_port = None
        self._cache_file_path = None
        self.ip = self._get_local_ip_address(ip)
        self._update_config_server_url()
        self._init_cache_file_path(cache_file_path)
        self._fetch_configuration()
        self._start_polling_thread()

    def _init_config_server_host_port(self):
        """
        Initialize the config server host and port
        """

        remote = self._config_server_url.split(":")
        self._config_server_host = f"{remote[0]}:{remote[1]}"
        if len(remote) == 1:
            self._config_server_port = 8090
        else:
            self._config_server_port = int(remote[2].rstrip("/"))

    def _init_cache_file_path(self, cache_file_path):
        """
        Initialize the cache file path
        """

        if cache_file_path is None:
            self._cache_file_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "config"
            )
        else:
            self._cache_file_path = cache_file_path

        if not os.path.isdir(self._cache_file_path):
            os.mkdir(self._cache_file_path)

    @staticmethod
    def _sign_string(string_to_sign: str, secret: str) -> str:
        signature = hmac.new(
            secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def _url_to_path_with_query(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return path + query

    def _build_http_headers(self, url: str, app_id: str, secret: str) -> Dict[str, str]:
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

    def _start_polling_thread(self) -> None:
        """
        Start the long polling loop thread
        """

        t = threading.Thread(target=self._listener)
        t.setDaemon(True)
        t.start()
        logger.success("Apollo polling thread started")

    def _http_get(self, url: str, params: Dict = None) -> requests.Response:
        """
        Handle http request with get method

        Auth logic according to: https://www.apolloconfig.com/#/zh/client/other-language-client-user-guide?id=_15-%e9%85%8d%e7%bd%ae%e8%ae%bf%e9%97%ae%e5%af%86%e9%92%a5
        """

        try:
            if self._app_secret:
                return requests.get(
                    url=url,
                    params=params,
                    timeout=self._timeout // 2,
                    headers=self._build_http_headers(
                        url, self._app_id, self._app_secret
                    ),
                )
            else:
                return requests.get(url=url, params=params, timeout=self._timeout // 2)

        except requests.exceptions.ReadTimeout:
            # if read timeout, check the server is alive or not
            try:
                with socket.create_connection(
                    (self._config_server_host, self._config_server_port),
                    timeout=self._timeout / 2,
                ):
                    # if connect server succeed, raise the exception that namespace not found
                    raise NameSpaceNotFoundException("namespace not found")
            except (ConnectionRefusedError, socket.timeout, OSError):
                # if connection refused, raise server not response error
                raise ServerNotResponseException(
                    "server: %s not response" % self._config_server_url
                )

    def _update_local_cache(
        self, release_key: str, data: str, namespace: str = "application"
    ) -> None:
        """
        Update local cache file if the release key is updated
        """

        # trans the config map to md5 string, and check it's been updated or not
        if self._hash.get(namespace) != release_key:
            # if it's updated, update the local cache file
            with open(
                os.path.join(
                    self._cache_file_path,
                    "%s_configuration_%s.txt" % (self._app_id, namespace),
                ),
                "w",
            ) as f:
                new_string = json.dumps(data)
                f.write(new_string)
            self._hash[namespace] = release_key

    def _get_local_cache(self, namespace: str = "application") -> Dict:
        """
        Get configuration from local cache file
        """
        cache_file_path = os.path.join(
            self._cache_file_path, "%s_configuration_%s.txt" % (self._app_id, namespace)
        )
        if os.path.isfile(cache_file_path):
            with open(cache_file_path, "r") as f:
                result = json.loads(f.readline())
            return result
        return {}

    def _fetch_config_by_namespace(self, namespace: str = "application") -> None:
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
                self._cache[namespace] = configurations

                self._update_local_cache(
                    release_key=release_key,
                    data=configurations,
                    namespace=namespace,
                )
            else:
                logger.warning(
                    "Get configuration from apollo failed, load from local cache file"
                )
                data = self._get_local_cache(namespace)
                self._cache[namespace] = data

        except Exception as e:
            logger.error(
                f"Fetch apollo configuration meet error, error: {e}, config server url: {self._config_server_url}, host: {self._config_server_host}, port: {self._config_server_port}"
            )
            data = self._get_local_cache(namespace)
            self._cache[namespace] = data

            self._update_config_server_url()

    def _update_config_server_url(self):
        """
        Update the config server url
        """

        self._config_server_url = self.get_config_server_url()
        self._init_config_server_host_port()

    def _fetch_configuration(self) -> None:
        """
        Get configurations for all namespaces from apollo server
        """

        try:
            for namespace in self._notification_map.keys():
                self._fetch_config_by_namespace(namespace)
        except requests.exceptions.ReadTimeout as e:
            logger.warning(str(e))
        except requests.exceptions.ConnectionError as e:
            logger.warning(str(e))
            self._load_local_cache_file()

    def _load_local_cache_file(self) -> bool:
        """
        Load local cache file to memory
        """

        for file_name in os.listdir(self._cache_file_path):
            file_path = os.path.join(self._cache_file_path, file_name)
            if os.path.isfile(file_path):
                file_simple_name, file_ext_name = os.path.splitext(file_name)
                if file_ext_name == ".swp":
                    continue
                namespace = file_simple_name.split("_")[-1]
                with open(file_path) as f:
                    self._cache[namespace] = json.loads(f.read())["configurations"]
        return True

    def _listener(self) -> None:
        """
        Long polling loop to get configuration from apollo server
        """

        while True:
            self._fetch_configuration()
            time.sleep(self._cycle_time)

    def get_config_server_url(self) -> str:
        """
        Get the config server url
        """

        service_conf_url = f"{self._meta_server_address}/services/config"
        service_conf: list = requests.get(service_conf_url).json()
        if not service_conf:
            raise ValueError("no apollo service found")
        service = service_conf[0]
        return service["homepageUrl"]

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
        except BasicException as e:
            logger.error(f"Get key({key}) value failed, error: {e}")
            return default_val

    def get_json_value(self, key: str, namespace: str = "application") -> Any:
        """
        Get the configuration value and convert it to json format
        """

        val = self.get_value(key, namespace=namespace)
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            logger.error(f"The value of key({key}) is not json format")
        return {}
