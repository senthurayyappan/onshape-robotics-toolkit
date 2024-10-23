import matplotlib.pyplot as plt
import networkx as nx

from onshape_api.models.assembly import (
    Instance,
    InstanceType,
    MateFeatureData,
    Occurrence,
    Part,
    SubAssembly,
)
from onshape_api.utilities.logging import LOGGER


def create_graph(
    occurences: dict[str, Occurrence],
    instances: dict[str, Instance],
    subassemblies: dict[str, SubAssembly],
    parts: dict[str, Part],
    mates: dict[str, MateFeatureData],
):
    graph = nx.DiGraph()

    for occurence in occurences:
        if instances[occurence].type == InstanceType.PART:
            try:
                graph.add_node(parts[occurence].partId, type=InstanceType.PART, id=occurence)
            except KeyError:
                LOGGER.warning(f"Part {occurence} not found")

    nx.draw(graph, with_labels=True)
    plt.show()
