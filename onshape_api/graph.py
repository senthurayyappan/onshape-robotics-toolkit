"""
This module contains functions to create and manipulate graphs from Onshape assembly data.

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


def get_root_node(graph: nx.DiGraph) -> str:
    """
    Get the root node of a directed graph.

    Args:
        graph: The directed graph.

    Returns:
        The root node of the graph.

    Examples:
        >>> graph = nx.DiGraph()
        >>> get_root_node(graph)
    """
    return next(nx.topological_sort(graph))


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


def get_topological_order(graph: nx.DiGraph) -> tuple[str]:
    """
    Get the topological order of a directed graph.

    Args:
        graph: The directed graph.

    Returns:
        The topological order of the graph.

    Examples:
        >>> graph = nx.DiGraph()
        >>> get_topological_order(graph)
    """
    try:
        order = tuple(nx.topological_sort(graph))
    except nx.NetworkXUnfeasible:
        LOGGER.warning("Graph has one or more cycles")
        order = None

    return order


def create_graph(
    occurences: dict[str, Occurrence],
    instances: dict[str, Union[PartInstance, AssemblyInstance]],
    parts: dict[str, Part],
    mates: dict[str, MateFeatureData],
) -> tuple[nx.DiGraph, str]:
    """
    Create a graph from onshape assembly data.

    Args:
        occurences: Dictionary of occurrences in the assembly.
        instances: Dictionary of instances in the assembly.
        parts: Dictionary of parts in the assembly.
        mates: Dictionary of mates in the assembly.

    Returns:
        The graph created from the assembly data.

    Examples:
        >>> occurences = get_occurences(assembly)
        >>> instances = get_instances(assembly)
        >>> parts = get_parts(assembly, client)
        >>> mates = get_mates(assembly)
        >>> create_graph(occurences, instances, parts, mates, directed=True)
    """

    graph: nx.Graph = nx.Graph()

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
            graph.add_edge(parent, child, **mates[mate].model_dump())
        except KeyError:
            LOGGER.warning(f"Mate {mate} not found")

    graph, root_node = convert_to_digraph(graph)

    LOGGER.info(f"Graph created with {len(graph.nodes)} nodes and {len(graph.edges)} edges with root node: {root_node}")

    return graph, root_node
