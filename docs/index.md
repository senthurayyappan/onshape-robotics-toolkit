<!-- [![Release](https://img.shields.io/github/v/release/senthurayyappan/onshape-api)](https://img.shields.io/github/v/release/senthurayyappan/onshape-api)
[![Build status](https://img.shields.io/github/actions/workflow/status/senthurayyappan/onshape-api/main.yml?branch=main)](https://github.com/senthurayyappan/onshape-api/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/senthurayyappan/onshape-api)](https://img.shields.io/github/commit-activity/m/senthurayyappan/onshape-api)
[![License](https://img.shields.io/github/license/senthurayyappan/onshape-api)](https://img.shields.io/github/license/senthurayyappan/onshape-api) -->

`onshape-api` is a Python library designed to interface with Onshape's REST API. It allows users to retrieve CAD data, modify it, and export it as a URDF (Unified Robot Description Format) for use in robotic system simulations.

## Features

    - Access and manipulate CAD data from Onshape documents.
    - Update variables and elements within Onshape documents.
    - Convert Onshape assemblies to URDF format for robotic simulations.

## Prerequisites

Before you begin, ensure you have the following:

- [Python 3.10](https://www.python.org/downloads/release/python-3100/) or higher installed on your machine.
- [An Onshape account](https://www.onshape.com/en/) if you don't already have one.
- [Onshape API keys (access key and secret key)](https://onshape-public.github.io/docs/auth/apikeys/)

## Installation

You can install `onshape-api` using `pip`, which is the easiest way to install it and is the recommended method for most users.

```sh
pip install onshape-api
```

If you want to install from source, you'll need to install [`poetry`](https://python-poetry.org/docs/) and [`git`](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) first. Then, you can clone the repository and install the package.

```sh
git clone #
cd onshape-api
poetry install
```

## Contributing

If you're interested in contributing to the project, please read the [contributing guidelines](#) to get started. All contributions are welcome!

## License

This project is licensed under the Apache 2.0 License. For more information, please refer to the [license](#) file.

## References

- [Onshape API Documentation](https://onshape-public.github.io/docs/)
- [Onshape API Glassworks Explorer](https://cad.onshape.com/glassworks/explorer/#/)
- [Onshape to Robot URDF Exporter](https://github.com/Rhoban/onshape-to-robot)
