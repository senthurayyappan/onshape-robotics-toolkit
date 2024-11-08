from typing import Union

import matplotlib.pyplot as plt
import networkx as nx

from onshape_api.log import LOGGER
from onshape_api.models.assembly import (
    AssemblyInstance,
    InstanceType,
    MateFeatureData,
    Occurrence,
    Part,
    PartInstance,
)
from onshape_api.parse import MATE_JOINER


def show_graph(graph: nx.Graph):
    nx.draw_circular(graph, with_labels=True)
    plt.show()


def save_graph(graph: nx.Graph, file_name: str):
    nx.draw_circular(graph, with_labels=True)
    plt.savefig(file_name)


def convert_to_digraph(graph: nx.Graph) -> nx.DiGraph:
    _centrality = nx.closeness_centrality(graph)
    _root_node = max(_centrality, key=_centrality.get)
    _graph = nx.bfs_tree(graph, _root_node)
    return _graph, _root_node


def create_graph(
    occurences: dict[str, Occurrence],
    instances: dict[str, Union[PartInstance, AssemblyInstance]],
    parts: dict[str, Part],
    mates: dict[str, MateFeatureData],
    directed: bool = True,
):
    graph = nx.Graph()

    for occurence in occurences:
        if instances[occurence].type == InstanceType.PART:
            try:
                if occurences[occurence].hidden:
                    continue

                graph.add_node(occurence, **parts[occurence].model_dump())
            except KeyError:
                LOGGER.warning(f"Part {occurence} not found")

    for mate in mates:
        try:
            child, parent = mate.split(MATE_JOINER)
            graph.add_edge(child, parent, **mates[mate].model_dump())
        except KeyError:
            LOGGER.warning(f"Mate {mate} not found")

    if directed:
        graph = convert_to_digraph(graph)

    LOGGER.info(f"Graph created with {len(graph.nodes)} nodes and {len(graph.edges)} edges")

    return graph
