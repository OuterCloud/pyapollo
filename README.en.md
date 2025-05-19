# pyapollo

- [English](README.en.md)
- [中文](README.md)

## Introduction

Apollo Python client using the official Apollo HTTP API.

Tested with Python 3.13 and the latest version of Apollo.

## Key Features

- Real-time updates: Supports configuration fetching and real-time updates.
- Secret support: Works with both secret-protected and non-secret Apollo applications.
- Distributed deployment: Supports configuration fetching from distributed Apollo deployments.
- Failover mechanism: Automatically switches to available service nodes when one becomes unavailable.
- Async support: Provides asynchronous support for fetching configuration items.

## Why This Project

The [Apollo official website](https://www.apolloconfig.com/#/en/client/python-sdks-user-guide) recommends three Python clients, each with issues:

1. [Client 1 project](https://github.com/filamoon/pyapollo) is no longer functional and was abandoned in 2019.

2. [Client 2 project](https://github.com/BruceWW/pyapollo) uses the telnetlib library, which is deprecated in Python 3.13. Additionally, some URLs return 404 errors. After reviewing the latest Apollo documentation, updates were needed. I considered contributing fixes, but ended up making significant changes beyond just adding app secret support, including various logic modifications and deletions. Rather than submitting a PR to author BruceWW, I created this new project, keeping the pyapollo name.

3. [Client 3 project](https://github.com/xhrg-product/apollo-client-python) states in its README that it's deprecated, so I didn't test it.

## Implementation Principle

As explained in Apollo's [Design Documentation](https://www.apolloconfig.com/#/en/design/apollo-introduction?id=_45-design):

- Meta Server encapsulates Eureka's service discovery interface.
- Clients access Config Service lists (IP+Port) via Meta Server domain names, then directly access services using IP+Port to get configurations.

This project implements this approach. The service discovery interface [source code is here](https://github.com/apolloconfig/apollo/blob/6de040a2b9bc68d32c95045de00e21f55f20122b/apollo-portal/src/main/java/com/ctrip/framework/apollo/portal/controller/SystemInfoController.java#L45).

## Installation

Install via pip:

```bash
pip install git+https://github.com/OuterCloud/pyapollo.git@main
```

Or add to requirements.txt:

```
git+https://github.com/OuterCloud/pyapollo.git@main
```

## Usage

The parameters in the following code snippets are explained as follows:

- meta_server_address: Apollo server address.
- app_id: Apollo application ID.
- app_secret: Apollo application secret key.

### Synchronous Apollo Client

```python
from pyapollo.client import ApolloClient

meta_server_address = "https://your-apollo/meta-server-address"
app_id="your-apollo-app-id"
app_secret="your-apollo-app-secret"

# Apollo sync client with app secret
apollo = ApolloClient(
    meta_server_address=meta_server_address,
    app_id=app_id,
    app_secret=app_secret,
)

# Apollo sync client without app secret
apollo = ApolloClient(
    meta_server_address=meta_server_address,
    app_id=app_id,
)

# Get text format configuration item
val = apollo.get_value("text_key")
print(val)

# Get JSON format configuration item
json_val = apollo.get_json_value("json_key")
print(json_val)
```

### Asynchronous Apollo Client

```python
import argparse
import asyncio

from pyapollo.async_client import AsyncApolloClient


async def main():
    meta_server_address = "https://your-apollo/meta-server-address"
    app_id="your-apollo-app-id"
    app_secret="your-apollo-app-secret"

    # Apollo async client with app secret
    async with AsyncApolloClient(
        meta_server_address=meta_server_address,
        app_id=app_id,
        app_secret=app_secret,
    ) as client:
        # Get text format configuration item
        val = await client.get_json_value("json_key")
        print(val)

        # Get JSON format configuration item
        json_val = await client.get_value("text_key")
        print(json_val)

    # Apollo async client without app secret
    async with AsyncApolloClient(
        meta_server_address=meta_server_address,
        app_id=app_id,
    ) as client:
        # Get text format configuration item
        val = await client.get_json_value("json_key")
        print(val)

        # Get JSON format configuration item
        json_val = await client.get_value("text_key")
        print(json_val)


if __name__ == "__main__":
    asyncio.run(main())
```
