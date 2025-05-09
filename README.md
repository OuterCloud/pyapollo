# pyapollo

Apollo python client using the official apollo http API.

在 Python 3.13 以及最新版的 Apollo 上已经测试通过。

主要功能：

- 支持实时更新：支持 Apollo 配置项获取与实时更新。
- 支持密钥：支持有密钥/无密钥的 Apollo 应用配置获取。
- 支持分布式部署：支持基于分布式部署的 Apollo 应用配置获取。
- 有容灾机制：当一个 Apollo 服务节点不可用时，会自动切换到下一个可用的服务节点。

## 为什么写这个项目

[Apollo 官网](https://www.apolloconfig.com/#/zh/client/python-sdks-user-guide)推荐了三个 Python 客户端，分别有以下问题：

1. 客户端 1 项目现在已经用不了了，在 2019 年就停止维护了。

2. 客户端 2 项目里面用了 telnetlib 库，这个标准库在 python 3.13 中已经 deprecated 了，还有里面的 url 我试了下已经 404 了，看了下最新的 apollo 官方文档，可能需要更新了。我想在此基础上改一改，但这一改，除了加了支持 app secret 的一些逻辑，还改了不少零零碎碎的地方，删了一些逻辑，所以我就不给作者 BruceWW 提 PR 了。直接新建了一个项目，还是叫 pyapollo。

3. 客户端 3 项目 readme 里说已经废弃了？我就没试了。

## 原理

在 Apollo 官方文档[总体设计](https://www.apolloconfig.com/#/zh/design/apollo-introduction?id=_45-%e6%80%bb%e4%bd%93%e8%ae%be%e8%ae%a1)中说过:

- Meta Server 用于封装 Eureka 的 服务发现接口。
- Client 通过域名访问 Meta Server 获取 Config Service 服务列表（IP+Port），而后直接通过 IP+Port 访问服务端获取配置信息。

本项目就是基于这个原理实现的。

## 安装

通过 pip 安装：

```bash
pip install git+https://github.com/OuterCloud/pyapollo.git@main
```

写到 requirements.txt 里也是一样：

```
git+https://github.com/OuterCloud/pyapollo.git@main
```

## 使用方法

```python
from pyapollo.client import ApolloClient

meta_server_address = "https://your-apollo/meta-server-address"
app_id="your-apollo-app-id"
app_secret="your-apollo-app-secret"

# 有鉴权的 Apollo 客户端
apollo = ApolloClient(
    meta_server_address=meta_server_address,
    app_id=app_id,
    app_secret=app_secret,
)

# 无鉴权的 Apollo 客户端
apollo = ApolloClient(
    meta_server_address=meta_server_address,
    app_id=app_id,
)

# 获取配置项
val = apollo.get("key")
print(val)
```
