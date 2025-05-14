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

Parameters:

- `meta_server_address`: Apollo server address
- `app_id`: Apollo application ID
- `app_secret`: Apollo application secret (optional for non-secret protected apps)

```python
from pyapollo.client import ApolloClient

meta_server_address = "https://your-apollo/meta-server-address"
app_id="your-apollo-app-id"
app_secret="your-apollo-app-secret"

# Apollo client with authentication
apollo = ApolloClient(
    meta_server_address=meta_server_address,
    app_id=app_id,
    app_secret=app_secret,
)

# Apollo client without authentication
apollo = ApolloClient(
    meta_server_address=meta_server_address,
    app_id=app_id,
)

# Get configuration values
val = apollo.get_value("key1")
print(val)

json_val = apollo.get_json_value("key2")
print(json_val)
```
