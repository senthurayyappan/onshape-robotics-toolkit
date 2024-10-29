import io
import random
from typing import Optional, Union

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import stl

from onshape_api.connect import Client
from onshape_api.models.assembly import (
    MATETYPE,
    Instance,
    InstanceType,
    MateFeatureData,
    Occurrence,
    Part,
)
from onshape_api.models.geometry import MeshGeometry
from onshape_api.models.joint import FixedJoint, JointLimits, RevoluteJoint
from onshape_api.models.link import (
    COLORS,
    Axis,
    CollisionLink,
    Inertia,
    InertialLink,
    Link,
    Material,
    Origin,
    VisualLink,
)
from onshape_api.models.mass import MassModel
from onshape_api.parse import MATE_JOINER, SUBASSEMBLY_JOINER
from onshape_api.utilities.logging import LOGGER
from onshape_api.utilities.mesh import transform_mesh


def generate_names(max_length: int) -> list[str]:
    with open("/Users/holycow/Projects/onshape-api/onshape_api/words.txt") as file:
        words = file.read().splitlines()

    if max_length > len(words):
        raise ValueError("max_length exceeds the number of available words")

    return random.sample(words, max_length)


def show_graph(graph: nx.Graph):
    nx.draw_circular(graph, with_labels=True)
    plt.show()


def convert_to_digraph(graph: nx.Graph) -> nx.DiGraph:
    _centrality = nx.closeness_centrality(graph)
    _root_node = max(_centrality, key=_centrality.get)
    _graph = nx.bfs_tree(graph, _root_node)
    return _graph, _root_node


def create_graph(
    occurences: dict[str, Occurrence],
    instances: dict[str, Instance],
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

    return graph


def flip_tuple(t: tuple) -> tuple:
    return t[::-1]


def download_stl_mesh(did, wid, eid, partID, client: Client, transform: np.ndarray = None, path: Optional[str] = None):
    if transform is None:
        transform = np.eye(4)

    buffer = io.BytesIO()
    client.download_stl(did, wid, eid, partID, buffer)
    buffer.seek(0)

    raw_mesh = stl.mesh.Mesh.from_file(None, fh=buffer)
    transformed_mesh = transform_mesh(raw_mesh, transform)
    transformed_mesh.save(path)

    return path


def get_urdf_components(
    graph: Union[nx.Graph, nx.DiGraph],
    workspaceId: str,
    parts: dict[str, Part],
    mass_properties: dict[str, MassModel],
    mates: dict[str, MateFeatureData],
    client: Client,
):
    if not isinstance(graph, nx.DiGraph):
        graph, root_node = convert_to_digraph(graph)

    joints = []
    links = []

    _child_transforms = {}
    _sorted_nodes = list(nx.topological_sort(graph))

    _names = generate_names(len(_sorted_nodes))
    _names_to_node_mapping = dict(zip(_sorted_nodes, _names))

    for node in _sorted_nodes:
        for edge in graph.edges(node):
            # check if the mate is between root assembly and subassembly
            if "".join(edge).count(SUBASSEMBLY_JOINER) == 1:
                _mate_key = MATE_JOINER.join(edge)
            else:
                _mate_key = MATE_JOINER.join(flip_tuple(edge))

            if _mate_key in mates:
                if mates[_mate_key].mateType == MATETYPE.REVOLUTE:
                    _child_transforms[node] = mates[_mate_key].matedEntities[0].matedCS.part_to_mate_transform
                    joints.append(
                        RevoluteJoint(
                            name=f"joint_{_names_to_node_mapping[edge[0]]}_{_names_to_node_mapping[edge[1]]}",
                            parent=_names_to_node_mapping[edge[0]],
                            child=_names_to_node_mapping[edge[1]],
                            origin=Origin.from_matrix(mates[_mate_key].matedEntities[1].matedCS.part_to_mate_transform),
                            limits=JointLimits(effort=1.0, velocity=1.0, lower=-1.0, upper=1.0),
                            axis=Axis((0, 1, 0)),
                        )
                    )

                elif mates[_mate_key].mateType == MATETYPE.FASTENED:
                    _child_transforms[node] = mates[_mate_key].matedEntities[0].matedCS.part_to_mate_transform
                    joints.append(
                        FixedJoint(
                            name=f"joint_{_names_to_node_mapping[edge[0]]}_{_names_to_node_mapping[edge[1]]}",
                            parent=_names_to_node_mapping[edge[0]],
                            child=_names_to_node_mapping[edge[1]],
                            origin=Origin.from_matrix(mates[_mate_key].matedEntities[1].matedCS.part_to_mate_transform),
                        )
                    )

    for node in _sorted_nodes:
        _link_to_stl_transform = np.eye(4)
        _mass_property = mass_properties.get(node)
        _mass = _mass_property.mass[0]
        _default_origin = Origin.zero_origin()

        if node in _child_transforms:
            _link_to_stl_transform = _child_transforms[node]
        else:
            _link_to_stl_transform[:3, 3] = np.array(_mass_property.center_of_mass).reshape(3)

        _stl_to_link_transform = np.matrix(np.linalg.inv(_link_to_stl_transform))

        _center_of_mass = _mass_property.center_of_mass_wrt(_stl_to_link_transform)
        _inertia_matrix = _mass_property.inertia_wrt(np.matrix(_stl_to_link_transform[:3, :3]))
        _default_principal_axes = (0, 0, 0)

        stl_path = download_stl_mesh(
            parts[node].documentId,
            workspaceId,
            parts[node].elementId,
            parts[node].partId,
            client,
            f"{_names_to_node_mapping[node]}.stl",
        )

        links.append(
            Link(
                name=_names_to_node_mapping[node],
                visual=VisualLink(
                    origin=_default_origin,
                    geometry=MeshGeometry(stl_path),
                    material=Material.from_color(name=f"{_names_to_node_mapping[node]}_material", color=COLORS.RED),
                ),
                inertial=InertialLink(
                    origin=Origin(_center_of_mass, _default_principal_axes),
                    mass=_mass,
                    inertia=Inertia(
                        ixx=_inertia_matrix[0, 0],
                        iyy=_inertia_matrix[1, 1],
                        izz=_inertia_matrix[2, 2],
                        ixy=_inertia_matrix[0, 1],
                        ixz=_inertia_matrix[0, 2],
                        iyz=_inertia_matrix[1, 2],
                    ),
                ),
                collision=CollisionLink(origin=_default_origin, geometry=MeshGeometry(stl_path)),
            )
        )
    return links, joints
