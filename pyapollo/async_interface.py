"""
Abstract interface for asynchronous configuration client implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AsyncConfigClientInterface(ABC):
    """Abstract base class for asynchronous configuration client implementations."""

    @abstractmethod
    async def get_value(
        self, key: str, default_val: str = None, namespace: str = "application"
    ) -> Any:
        """
        Get configuration value for the given key.

        Args:
            key: The configuration key to get value for
            default_val: Default value to return if key doesn't exist
            namespace: The namespace to get configuration from

        Returns:
            The configuration value or default value if key doesn't exist
        """
        pass

    @abstractmethod
    async def get_json_value(self, key: str, namespace: str = "application") -> Any:
        """
        Get configuration value and parse it as JSON.

        Args:
            key: The configuration key to get JSON value for
            namespace: The namespace to get configuration from

        Returns:
            The parsed JSON value or empty dict if parsing fails
        """
        pass

    @abstractmethod
    async def get_service_conf(self) -> List:
        """
        Get the configuration service information.

        Returns:
            List of configuration service information
        """
        pass

    @abstractmethod
    async def fetch_configuration(self) -> None:
        """
        Fetch latest configuration from the configuration server.
        This method should handle the core logic of retrieving configuration.
        """
        pass

    @abstractmethod
    async def start_polling(self) -> None:
        """
        Start background task for polling configuration updates.
        """
        pass

    @abstractmethod
    async def stop_polling(self) -> None:
        """
        Stop the background polling task.
        """
        pass

    @abstractmethod
    async def load_local_cache_file(self) -> bool:
        """
        Load configuration from local cache files.

        Returns:
            True if loading was successful, False otherwise
        """
        pass

    @abstractmethod
    async def update_local_file_cache(
        self, release_key: str, data: Any, namespace: str = "application"
    ) -> None:
        """
        Update local cache file with new configuration data.

        Args:
            release_key: The release key for the configuration
            data: The configuration data to cache
            namespace: The namespace of the configuration
        """
        pass

    @abstractmethod
    async def update_config_server(self, exclude: Optional[str] = None) -> str:
        """
        Update the configuration server information.

        This method is responsible for service discovery and updating the client's
        configuration server endpoints. It may involve fetching server information
        from a meta server, selecting an appropriate server, and updating internal
        connection details.

        Args:
            exclude: Optional server to exclude from selection

        Returns:
            The selected configuration server URL or identifier
        """
        pass

    @abstractmethod
    async def update_cache(self, namespace: str, data: Dict) -> None:
        """
        Update in-memory configuration cache.

        Args:
            namespace: The namespace of the configuration
            data: The configuration data to cache
        """
        pass

    @abstractmethod
    async def fetch_config_by_namespace(self, namespace: str = "application") -> None:
        """
        Fetch configuration of the specific namespace from configuration server.

        Args:
            namespace: The namespace to fetch configuration for
        """
        pass

    @abstractmethod
    async def get_local_file_cache(self, namespace: str = "application") -> Dict:
        """
        Get configuration from local cache file.

        Args:
            namespace: The namespace to get configuration for

        Returns:
            The configuration data from local cache file
        """
        pass

    @abstractmethod
    async def __aenter__(self):
        """Enter the async context manager."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        pass
