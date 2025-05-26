"""
Test script for ApolloSettingsConfig with different namespaces formats.
"""

from pyapollo.settings import ApolloSettingsConfig


# pytest -vs tests/test_settings.py::test_env_file
def test_env_file():
    """Test loading settings from env file with different namespaces formats."""
    try:
        # Test with test.env file
        settings = ApolloSettingsConfig.from_env_file("tests/example.env")
        print("\nTest with test.env file:")
        print(f"Namespaces: {settings.namespaces}")

        # Test with direct initialization - string format
        settings = ApolloSettingsConfig(
            meta_server_address="http://localhost:8080",
            app_id="test-app",
            namespaces="app1,app2,app3",
        )
        print("\nTest with string format:")
        print(f"Namespaces: {settings.namespaces}")

        # Test with direct initialization - list format
        settings = ApolloSettingsConfig(
            meta_server_address="http://localhost:8080",
            app_id="test-app",
            namespaces=["app1", "app2", "app3"],
        )
        print("\nTest with list format:")
        print(f"Namespaces: {settings.namespaces}")

        # Test with default value
        settings = ApolloSettingsConfig(
            meta_server_address="http://localhost:8080", app_id="test-app"
        )
        print("\nTest with default value:")
        print(f"Namespaces: {settings.namespaces}")

    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        raise


if __name__ == "__main__":
    test_env_file()
