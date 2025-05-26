"""
Demo for using Apollo client with environment variables configuration.

This example demonstrates how to configure Apollo client using environment variables.
Before running this script, make sure to set the required environment variables:

# Required environment variables:
export APOLLO_META_SERVER_ADDRESS=http://localhost:8080
export APOLLO_APP_ID=your-app-id

# Optional environment variables:
export APOLLO_USING_APP_SECRET=true  # Set to true if using authentication
export APOLLO_APP_SECRET=your-app-secret  # Required if APOLLO_USING_APP_SECRET is true
export APOLLO_CLUSTER=default
export APOLLO_ENV=DEV
export APOLLO_NAMESPACES=application,common  # Comma-separated list of namespaces
export APOLLO_TIMEOUT=10
export APOLLO_CYCLE_TIME=30

Run this script:
    python examples/env_demo.py --key your_config_key
    python examples/env_demo.py --key your_config_key --json-key your_json_key
"""

import os
import argparse
from pyapollo.client import ApolloClient


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Demo for Apollo client with environment variables configuration"
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


def main():
    # Parse command line arguments
    args = parse_args()
    config_key = args.key
    json_key = args.json_key or config_key  # Use the same key for JSON if not specified

    # Print current Apollo-related environment variables
    print("Current Apollo Environment Variables:")
    for key, value in os.environ.items():
        if key.startswith("APOLLO_"):
            # Mask the secret if present
            if "SECRET" in key:
                value = "*" * len(value)
            print(f"{key}={value}")
    print()

    # Create Apollo client - it will automatically read from environment variables
    client = ApolloClient()

    # Get configuration values
    try:
        # Try to get a text configuration value
        text_value = client.get_value(config_key, default_val="default_value")
        print(f"Text configuration value for '{config_key}': {text_value}")

        # Try to get a JSON configuration value
        json_value = client.get_json_value(json_key, default_val={"status": "default"})
        print(f"JSON configuration value for '{json_key}': {json_value}")

    except Exception as e:
        print(f"Error getting configuration: {e}")


if __name__ == "__main__":
    main()
