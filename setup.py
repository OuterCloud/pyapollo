from setuptools import setup, find_packages

setup(
    name="pyapollo",  # 包名
    version="0.1.4",  # 版本
    author="lantianyou",
    author_email="434209210@qq.com",
    description="Apollo client tested on python 3.13",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/OuterCloud/pyapollo",
    packages=find_packages(),  # 自动查找模块
    install_requires=[
        "requests",
        "loguru",
    ],  # 依赖包列表
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.7",
)
