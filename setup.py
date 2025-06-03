from setuptools import setup, find_packages

setup(
    name="pyapollo",
    version="0.2.0",
    author="lantianyou",
    author_email="434209210@qq.com",
    description="Apollo client with async support and pydantic integration, tested on python 3.13",
    long_description=open("README.md", encoding='utf-8').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/OuterCloud/pyapollo",
    packages=find_packages(),
    install_requires=[
        "setuptools",
        "requests",
        "loguru",
        "aiohttp",
        "aiofiles",
        "pydantic-settings",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Framework :: AsyncIO",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
)
