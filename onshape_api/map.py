import os
from functools import partial
from typing import Optional

import matplotlib.pyplot as plt
import networkx as nx

from onshape_api.models.assembly import Assembly, Instance

os.environ['TCL_LIBRARY'] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ['TK_LIBRARY'] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"


def create_graph(assembly: Assembly, save_path: str) -> nx.DiGraph:
    """
    Create a graph from the assembly structure

    Args:
        assembly: Assembly object

    Returns:
        nx.DiGraph: NetworkX DiGraph object
    """
    G = nx.DiGraph()
    G.add_node(assembly.rootAssembly.uid)

    nx.draw(G, with_labels=True)
    plt.show()

    return G


def traverse_assembly(assembly: Assembly):
    """
    Traverse the assembly structure

    Args:
        assembly: Assembly object
    """
    print(assembly.rootAssembly.uid)
    root = assembly.rootAssembly

    def get_instance(path: str, instances: Optional[list[Instance]] = None):
        """
        Get instance of an occurence path
        """
        if instances is None:
            instances = assembly.rootAssembly.instances

        for instance in instances:
            print(instance)
            if instance.id == path[0]:
                if len(path) == 1:
                    return instance
                else:
                    for sub_assembly in assembly.subAssemblies:
                        if sub_assembly.uid == instance.uid:
                            return get_instance(path[1:], sub_assembly.instances)

    # for occurence in root.occurrences:
    #     instance = get_instance(occurence.path, assembly)
    #     print(instance)





