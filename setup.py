from setuptools import setup, find_packages

setup(
    name="pyapollo",
    version="0.1.7",
    author="lantianyou",
    author_email="434209210@qq.com",
    description="Apollo client tested on python 3.13",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/OuterCloud/pyapollo",
    packages=find_packages(),
    install_requires=[
        "setuptools",
        "requests",
        "loguru",
        "aiohttp",
        "aiofiles",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.7",
)
