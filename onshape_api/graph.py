"""
This module contains functions to create and manipulate graphs from Onshape assembly data.

Functions:
    - **show_graph**: Display the graph using networkx and matplotlib.
    - **save_graph**: Save the graph as an image file.
    - **convert_to_digraph**: Convert a graph to a directed graph.
    - **create_graph**: Create a graph from assembly data.
"""

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


def show_graph(graph: nx.Graph) -> None:
    """
    Display the graph using networkx and matplotlib.

    Args:
        graph: The graph to display.

    Examples:
        >>> graph = nx.Graph()
        >>> show_graph(graph)
    """
    nx.draw_circular(graph, with_labels=True)
    plt.show()


def save_graph(graph: nx.Graph, file_name: str) -> None:
    """
    Save the graph as an image file.

    Args:
        graph: The graph to save.
        file_name: The name of the image file.

    Examples:
        >>> graph = nx.Graph()
        >>> save_graph(graph, "graph.png")
    """
    nx.draw_circular(graph, with_labels=True)
    plt.savefig(file_name)


def convert_to_digraph(graph: nx.Graph) -> nx.DiGraph:
    """
    Convert a graph to a directed graph and calculate the root node using closeness centrality.

    Args:
        graph: The graph to convert.

    Returns:
        The directed graph and the root node of the graph, calculated using closeness centrality.

    Examples:
        >>> graph = nx.Graph()
        >>> convert_to_digraph(graph)
        (digraph, root_node)
    """
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
) -> Union[nx.Graph, nx.DiGraph]:
    """
    Create a graph from onshape assembly data.

    Args:
        occurences: Dictionary of occurrences in the assembly.
        instances: Dictionary of instances in the assembly.
        parts: Dictionary of parts in the assembly.
        mates: Dictionary of mates in the assembly.
        directed: Whether the graph should be directed or not.

    Returns:
        The graph created from the assembly data.

    Examples:
        >>> occurences = get_occurences(assembly)
        >>> instances = get_instances(assembly)
        >>> parts = get_parts(assembly, client)
        >>> mates = get_mates(assembly)
        >>> create_graph(occurences, instances, parts, mates, directed=True)
    """

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
