"""Setup for cli-shim"""
from setuptools import setup, find_packages

setup(
    name="cli-shim",
    version="0.1.0",
    description="Universal Agent-Native CLI Adapter — makes legacy CLIs agent-friendly",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Yunare Maia",
    author_email="yunare@gmail.com",
    url="https://github.com/yunaremaia/cli-shim",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "shim=cli_shim:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Systems Administration",
    ],
)
