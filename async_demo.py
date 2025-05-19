import argparse
import asyncio

from pyapollo.async_client import AsyncApolloClient


async def main():
    parser = argparse.ArgumentParser(description="Apollo Config Fetcher")
    parser.add_argument("--meta", required=True, help="Apollo meta server address")
    parser.add_argument("--app-id", required=True, help="Application ID")
    parser.add_argument("--secret", help="Application secret")
    parser.add_argument("--key", default="config_local", help="Config key to fetch")
    parser.add_argument("--json", action="store_true", help="Parse as JSON")

    args = parser.parse_args()

    async with AsyncApolloClient(
        meta_server_address=args.meta,
        app_id=args.app_id,
        app_secret=args.secret,
    ) as client:
        if args.json:
            value = await client.get_json_value(args.key)
        else:
            value = await client.get_value(args.key)
        print(value)


if __name__ == "__main__":
    asyncio.run(main())
