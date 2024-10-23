import os

import matplotlib.pyplot as plt
import networkx as nx

from onshape_api.models.assembly import Assembly

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





