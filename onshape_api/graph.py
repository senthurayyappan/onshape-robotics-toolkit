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
from onshape_api.parse import MATE_JOINER, SUBASSEMBLY_JOINER
from onshape_api.utilities.helpers import print_dict
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
                if occurences[occurence].hidden:
                    continue

                graph.add_node(occurence, **parts[occurence].model_dump())
            except KeyError:
                LOGGER.warning(f"Part {occurence} not found")

        # elif instances[occurence].type == InstanceType.ASSEMBLY:
        #     try:
        #         graph.add_node(occurence, **subassemblies[occurence].model_dump())
        #     except KeyError:
        #         LOGGER.warning(f"SubAssembly {occurence} not found")

    for mate in mates:
        try:
            child, parent = mate.split(MATE_JOINER)
            print(child, parent)
            graph.add_edge(child, parent, **mates[mate].model_dump())
        except KeyError:
            LOGGER.warning(f"Mate {mate} not found")

    nx.draw_circular(graph, with_labels=True)
    plt.show()
