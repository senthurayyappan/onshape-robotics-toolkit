from importlib import metadata as importlib_metadata


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


__version__: str = get_version()

from onshape_api.connection import *  # noqa: F403 E402
from onshape_api.utilities import *  # noqa: F403 E402
