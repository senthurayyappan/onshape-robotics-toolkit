from importlib import metadata as importlib_metadata


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"


__version__: str = get_version()

from onshape_api.connect import *  # noqa: F403 E402
from onshape_api.graph import *  # noqa: F403 E402
from onshape_api.log import *  # noqa: F403 E402
from onshape_api.mesh import *  # noqa: F403 E402
from onshape_api.models import *  # noqa: F403 E402
from onshape_api.parse import *  # noqa: F403 E402
from onshape_api.urdf import *  # noqa: F403 E402
from onshape_api.utilities import *  # noqa: F403 E402
