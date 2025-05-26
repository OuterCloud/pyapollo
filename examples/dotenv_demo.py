"""
Demo for using Apollo client with .env file configuration.

This example demonstrates two ways to use .env files:
1. Default .env file in the project root
2. Custom .env file path

Example .env file content:
```
# Required Settings
APOLLO_META_SERVER_ADDRESS=http://localhost:8080
APOLLO_APP_ID=your-app-id

# Authentication Settings
APOLLO_USING_APP_SECRET=true
APOLLO_APP_SECRET=your-app-secret

# Optional Settings
APOLLO_CLUSTER=default
APOLLO_ENV=DEV
APOLLO_NAMESPACES=application,common
APOLLO_TIMEOUT=10
APOLLO_CYCLE_TIME=30
```

Run this script:
    python examples/dotenv_demo.py --key your_config_key
    python examples/dotenv_demo.py --key your_config_key --json-key your_json_key
"""

import os
import argparse
from pyapollo.client import ApolloClient
from pyapollo.settings import ApolloSettingsConfig


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Demo for Apollo client with .env file configuration"
    )
    parser.add_argument(
        "--key",
        default="sample_key",
        help="Configuration key to retrieve (default: sample_key)",
    )
    parser.add_argument(
        "--json-key", default=None, help="JSON configuration key to retrieve (optional)"
    )
    return parser.parse_args()


def print_config(settings: ApolloSettingsConfig):
    """Print the current Apollo configuration."""
    print("Current Apollo Configuration:")
    print(f"Meta Server: {settings.meta_server_address}")
    print(f"App ID: {settings.app_id}")
    print(f"Using Secret: {settings.using_app_secret}")
    if settings.using_app_secret:
        print(f"App Secret: {'*' * len(settings.app_secret or '')}")
    print(f"Cluster: {settings.cluster}")
    print(f"Environment: {settings.env}")
    print(f"Namespaces: {settings.namespaces}")
    print(f"Timeout: {settings.timeout}")
    print(f"Cycle Time: {settings.cycle_time}")


def demo_default_env_file(config_key: str, json_key: str):
    """Demonstrate using the default .env file."""
    print("=== Using Default .env File ===")
    try:
        # Create client using default .env file
        client = ApolloClient()
        print_config(client.settings)

        # Try to get some configuration values
        text_value = client.get_value(config_key, default_val="default_value")
        print(f"Text configuration value for '{config_key}': {text_value}")

        json_value = client.get_json_value(json_key, default_val={"status": "default"})
        print(f"JSON configuration value for '{json_key}': {json_value}")

    except Exception as e:
        print(f"Error with default .env file: {e}")


def demo_custom_env_file(config_key: str, json_key: str):
    """Demonstrate using a custom .env file."""
    print("=== Using Custom .env File ===")
    try:
        # Create settings from custom .env file
        settings = ApolloSettingsConfig.from_env_file("examples/test.env")
        client = ApolloClient(settings=settings)
        print_config(client.settings)

        # Try to get some configuration values
        text_value = client.get_value(config_key, default_val="default_value")
        print(f"Text configuration value for '{config_key}': {text_value}")

        json_value = client.get_json_value(json_key, default_val={"status": "default"})
        print(f"JSON configuration value for '{json_key}': {json_value}")

    except Exception as e:
        print(f"Error with custom .env file: {e}")


def main():
    """Run both demonstrations."""
    # Parse command line arguments
    args = parse_args()
    config_key = args.key
    json_key = args.json_key or config_key  # Use the same key for JSON if not specified

    # Check if default .env file exists
    if os.path.exists(".env"):
        demo_default_env_file(config_key, json_key)
    else:
        print("Default .env file not found in project root")
        print("Please create one using .env.example as a template")

    # Check if custom .env file exists
    if os.path.exists("examples/test.env"):
        demo_custom_env_file(config_key, json_key)
    else:
        print("Custom .env file not found at examples/test.env")
        print("Please create one using .env.example as a template")


if __name__ == "__main__":
    main()
