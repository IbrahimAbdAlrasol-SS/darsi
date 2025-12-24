#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="darsi-bot",
    version="1.0.0",
    author="VX",
    author_email="karajavam@telegram",
    description="A comprehensive school management bot for Telegram",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/L1053/darsi-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Education",
        "Topic :: Communications :: Chat",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "darsi-bot=main:main",
        ],
    },
    keywords="telegram bot school management education aiogram",
    project_urls={
        "Bug Reports": "https://github.com/L1053/darsi-bot/issues",
        "Source": "https://github.com/L1053/darsi-bot",
        "Documentation": "https://github.com/L1053/darsi-bot#readme",
    },
)
