# pyapollo

- [English](README.en.md)
- [中文](README.md)

## Introduction

A Python client for Apollo configuration service implemented using the official Apollo HTTP API. Tested with Python 3.13 and the latest version of Apollo.

Key Features:

- Real-time Updates: Supports Apollo configuration retrieval and real-time updates.
- Secret Support: Supports Apollo applications with or without secret keys.
- Distributed Deployment: Supports configuration retrieval for Apollo applications in distributed deployments.
- Fault Tolerance: Automatically switches to the next available service node when an Apollo service node is unavailable.
- Async Support: Provides an asynchronous client for async configuration retrieval.
- Multiple Configuration Methods: Supports configuration via environment variables, .env files, or direct parameters.

## Why This Project

[Apollo's official website](https://www.apolloconfig.com/#/zh/client/python-sdks-user-guide) recommends three Python clients, each with the following issues:

1. [Client 1](https://github.com/filamoon/pyapollo) is no longer functional and hasn't been maintained since 2019.

2. [Client 2](https://github.com/BruceWW/pyapollo) uses the telnetlib library, which is deprecated in Python 3.13. Additionally, some URLs in the project are now 404. After reviewing the latest Apollo documentation, updates were needed. Instead of submitting a PR with extensive changes, I created a new project.

3. [Client 3](https://github.com/xhrg-product/apollo-client-python) is marked as deprecated in its README.

## How It Works

According to Apollo's official documentation on [Overall Design](https://www.apolloconfig.com/#/zh/design/apollo-introduction?id=_45-%e6%80%bb%e4%bd%93%e8%ae%be%e8%ae%a1):

- Meta Server encapsulates Eureka's service discovery interface.
- Client accesses Meta Server through domain name to get Config Service list (IP+Port), then directly accesses the server through IP+Port to get configuration information.

This project is implemented based on this principle. The service discovery interface is defined in the [source code here](https://github.com/apolloconfig/apollo/blob/6de040a2b9bc68d32c95045de00e21f55f20122b/apollo-portal/src/main/java/com/ctrip/framework/apollo/portal/controller/SystemInfoController.java#L45).

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

Parameter descriptions:

- meta_server_address: Apollo server address.
- app_id: Apollo application ID.
- app_secret: Apollo application secret key.

### Configuration Methods

pyapollo supports multiple configuration methods, listed in order of priority (highest to lowest):

1. Direct Parameters: Pass parameters directly when creating the client
2. Using ApolloSettingsConfig: Create a settings object and pass it to the client
3. Environment Variables: Use environment variables with the APOLLO\_ prefix
4. .env File: Create a .env file in the project root directory

#### Using .env File

Create a `.env` file in your project root directory with the following content:

```
# Required Apollo Settings
APOLLO_META_SERVER_ADDRESS=http://localhost:8080
APOLLO_APP_ID=your-app-id

# Authentication Settings
APOLLO_USING_APP_SECRET=true
APOLLO_APP_SECRET=your-app-secret

# Optional Settings
APOLLO_CLUSTER=default
APOLLO_ENV=DEV
APOLLO_NAMESPACES=application,common,database
APOLLO_TIMEOUT=10
APOLLO_CYCLE_TIME=30
```

A `.env.example` file is provided as a reference.

##### Custom .env File Path

In addition to the default `.env` file in the project root, you can specify a custom .env file path:

```python
from pyapollo.settings import ApolloSettingsConfig
from pyapollo.client import ApolloClient

# Load from custom .env file path
settings = ApolloSettingsConfig.from_env_file("path/to/custom.env")
client = ApolloClient(settings=settings)
```

#### Using Environment Variables

Set environment variables directly:

```bash
# Required settings
export APOLLO_META_SERVER_ADDRESS=http://localhost:8080
export APOLLO_APP_ID=your-app-id

# Authentication settings (optional)
export APOLLO_USING_APP_SECRET=true
export APOLLO_APP_SECRET=your-app-secret

# Other optional settings
export APOLLO_CLUSTER=default
export APOLLO_ENV=DEV
export APOLLO_NAMESPACES=application,common,database
export APOLLO_TIMEOUT=10
export APOLLO_CYCLE_TIME=30
```

##### Supported Environment Variables

| Environment Variable       | Description                            | Default     | Required                      |
| -------------------------- | -------------------------------------- | ----------- | ----------------------------- |
| APOLLO_META_SERVER_ADDRESS | Apollo server address                  | -           | Yes                           |
| APOLLO_APP_ID              | Apollo application ID                  | -           | Yes                           |
| APOLLO_USING_APP_SECRET    | Whether to use secret authentication   | false       | No                            |
| APOLLO_APP_SECRET          | Apollo application secret key          | -           | Only if USING_APP_SECRET=true |
| APOLLO_CLUSTER             | Cluster name                           | default     | No                            |
| APOLLO_ENV                 | Environment name                       | DEV         | No                            |
| APOLLO_NAMESPACES          | Comma-separated list of namespaces     | application | No                            |
| APOLLO_TIMEOUT             | Request timeout in seconds             | 10          | No                            |
| APOLLO_CYCLE_TIME          | Configuration refresh cycle in seconds | 30          | No                            |
| APOLLO_CACHE_FILE_DIR_PATH | Cache file directory path              | -           | No                            |
| APOLLO_IP                  | Client IP address                      | -           | No                            |

#### Using ApolloSettingsConfig

```python
from pyapollo.settings import ApolloSettingsConfig
from pyapollo.client import ApolloClient

# Create settings object
settings = ApolloSettingsConfig(
    meta_server_address="http://localhost:8080",
    app_id="your-app-id",
    using_app_secret=True,
    app_secret="your-app-secret"
)

# Pass settings to client
client = ApolloClient(settings=settings)
```

### Synchronous Apollo Client

```python
from pyapollo.client import ApolloClient

# Method 1: Direct parameters
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

# Method 2: Load from environment variables or .env file
apollo = ApolloClient()  # Automatically loads from environment or .env file

# Get text format configuration
val = apollo.get_value("text_key")
print(val)

# Get JSON format configuration
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

    # Apollo async client with authentication
    async with AsyncApolloClient(
        meta_server_address=meta_server_address,
        app_id=app_id,
        app_secret=app_secret,
    ) as client:
        # Get text format configuration
        val = await client.get_json_value("json_key")
        print(val)

        # Get JSON format configuration
        json_val = await client.get_value("text_key")
        print(json_val)

    # Apollo async client without authentication
    async with AsyncApolloClient(
        meta_server_address=meta_server_address,
        app_id=app_id,
    ) as client:
        # Get text format configuration
        val = await client.get_json_value("json_key")
        print(val)

        # Get JSON format configuration
        json_val = await client.get_value("text_key")
        print(json_val)


if __name__ == "__main__":
    asyncio.run(main())
```

## Example Code

The project provides multiple example scripts demonstrating different configuration and usage methods:

### Synchronous Client Example

```bash
python examples/sync_demo.py
```

### Asynchronous Client Example

```bash
python examples/async_demo.py
```

### Environment Variables Configuration Example

```bash
# First set the required environment variables
export APOLLO_META_SERVER_ADDRESS=http://localhost:8080
export APOLLO_APP_ID=your-app-id

# Run the example (with default key name 'sample_key')
python examples/env_demo.py

# Run the example (with specified configuration key)
python examples/env_demo.py --key your_config_key

# Run the example (with different text and JSON configuration keys)
python examples/env_demo.py --key your_config_key --json-key your_json_key
```

### .env File Configuration Example

```bash
# Make sure you have a .env file in the project root or examples/test.env
# Using default key names
python examples/dotenv_demo.py

# Specify configuration key
python examples/dotenv_demo.py --key your_config_key

# Specify different text and JSON configuration keys
python examples/dotenv_demo.py --key your_config_key --json-key your_json_key
```
