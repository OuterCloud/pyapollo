"""
This is a demo script to fetch configuration from Apollo Config Service.
You can run it like this:
Get JSON value:
    python demo.py --meta META_SERVER_ADDRESS --app-id YOUR_APP_ID --secret YOUR_APP_SECRET --key YOUR_CONFIG_KEY --json
Get plain text value:
    python demo.py --meta META_SERVER_ADDRESS --app-id YOUR_APP_ID --secret YOUR_APP_SECRET --key YOUR_CONFIG_KEY
"""

import argparse
from pyapollo.client import ApolloClient


def main():
    parser = argparse.ArgumentParser(description="Apollo Config Fetcher")
    parser.add_argument("--meta", required=True, help="Apollo meta server address")
    parser.add_argument("--app-id", required=True, help="Application ID")
    parser.add_argument("--secret", help="Application secret")
    parser.add_argument("--key", default="config_local", help="Config key to fetch")
    parser.add_argument("--json", action="store_true", help="Parse as JSON")

    args = parser.parse_args()

    client = ApolloClient(
        meta_server_address=args.meta,
        app_id=args.app_id,
        app_secret=args.secret,
    )

    if args.json:
        val = client.get_json_value(args.key)
    else:
        val = client.get_value(args.key)

    print(val)


if __name__ == "__main__":
    main()
