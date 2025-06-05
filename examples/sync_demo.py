"""
This is a demo script to fetch configuration from Apollo Config Service.

Configuration can be provided in four ways:
1. Command line arguments (highest priority)
2. Environment variables
3. Custom .env file
4. Default .env file in current directory (lowest priority)

Environment variables:
    APOLLO_META_SERVER_ADDRESS: Apollo meta server address
    APOLLO_APP_ID: Application ID
    APOLLO_APP_SECRET: Application secret
    APOLLO_USING_APP_SECRET: Whether to use app secret (true/false)
    APOLLO_CLUSTER: Cluster name (default: default)
    APOLLO_ENV: Environment (default: DEV)
    APOLLO_NAMESPACES: Comma-separated list of namespaces (default: application)

.env file example:
    APOLLO_META_SERVER_ADDRESS=http://localhost:8080
    APOLLO_APP_ID=your-app-id
    APOLLO_USING_APP_SECRET=true
    APOLLO_APP_SECRET=your-app-secret

Examples:
1. Using command line arguments:
    python sync_demo.py --meta http://localhost:8080 --app-id your-app-id --secret your-secret --key your-key --json

2. Using environment variables:
    export APOLLO_META_SERVER_ADDRESS=http://localhost:8080
    export APOLLO_APP_ID=your-app-id
    export APOLLO_APP_SECRET=your-secret
    python sync_demo.py --key your-key --json

3. Using custom .env file:
    python sync_demo.py --env-file /path/to/custom.env --key your-key --json

4. Using default .env file:
    # Create .env file in current directory
    python sync_demo.py --use-env --key your-key --json
"""

import os
import argparse
from pyapollo.client import ApolloClient
from pyapollo.settings import ApolloSettingsConfig


def main():
    parser = argparse.ArgumentParser(description="Apollo Config Fetcher")

    # Configuration source arguments
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        "--use-env",
        action="store_true",
        help="Use environment variables or default .env file for configuration",
    )
    config_group.add_argument(
        "--env-file",
        help="Path to custom .env file for configuration",
    )
    config_group.add_argument(
        "--use-settings",
        action="store_true",
        help="Use ApolloSettingsConfig for configuration",
    )

    # Apollo configuration arguments
    parser.add_argument("--meta", help="Apollo meta server address")
    parser.add_argument("--app-id", help="Application ID")
    parser.add_argument("--secret", help="Application secret")
    parser.add_argument(
        "--cluster", default="default", help="Cluster name (default: default)"
    )
    parser.add_argument("--env", default="DEV", help="Environment (default: DEV)")
    parser.add_argument(
        "--namespaces",
        default="application",
        help="Comma-separated list of namespaces (default: application)",
    )

    # Value fetching arguments
    parser.add_argument("--key", default="config_local", help="Config key to fetch")
    parser.add_argument("--json", action="store_true", help="Parse as JSON")

    args = parser.parse_args()

    # Create Apollo client based on configuration source
    if args.use_env:
        # Use environment variables or default .env file
        client = ApolloClient()
    elif args.env_file:
        # Use custom .env file
        settings = ApolloSettingsConfig.from_env_file(args.env_file)
        client = ApolloClient(settings=settings)
    elif args.use_settings:
        # Use ApolloSettingsConfig
        settings = ApolloSettingsConfig(
            meta_server_address=args.meta or os.getenv("APOLLO_META_SERVER_ADDRESS"),
            app_id=args.app_id or os.getenv("APOLLO_APP_ID"),
            using_app_secret=bool(args.secret or os.getenv("APOLLO_APP_SECRET")),
            app_secret=args.secret or os.getenv("APOLLO_APP_SECRET"),
            cluster=args.cluster,
            env=args.env,
            namespaces=args.namespaces.split(",")
            if args.namespaces
            else ["application"],
        )
        client = ApolloClient(settings=settings)
    else:
        # Use command line arguments
        if not args.meta or not args.app_id:
            parser.error(
                "When not using --use-env, --env-file or --use-settings, "
                "--meta and --app-id are required"
            )

        client = ApolloClient(
            meta_server_address=args.meta,
            app_id=args.app_id,
            app_secret=args.secret,
            cluster=args.cluster,
            env=args.env,
            namespaces=args.namespaces.split(",")
            if args.namespaces
            else ["application"],
        )

    # Fetch and print value
    try:
        if args.json:
            val = client.get_json_value(args.key)
        else:
            val = client.get_value(args.key)
        print(val)
    except Exception as e:
        print(f"Error fetching value: {e}")
    finally:
        # Stop the polling thread
        client.stop_polling_thread()


if __name__ == "__main__":
    main()
