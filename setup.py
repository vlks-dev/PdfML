#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# Чтение версии из файла __init__.py
with open(os.path.join("pdfml", "__init__.py"), "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

# Чтение README.md для длинного описания
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Чтение requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="pdfml",
    version=version,
    description="Библиотека для извлечения данных из PDF с помощью ML",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Vladimir Kosov",
    author_email="author@example.com",
    url="https://github.com/author/pdfml",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.8",
    keywords="pdf, machine learning, data extraction, ocr, text extraction",
) 