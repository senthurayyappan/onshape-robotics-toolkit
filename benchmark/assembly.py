import cProfile
import json
import os
import pstats

import pandas as pd

from onshape_api.connect import Client
from onshape_api.graph import create_graph, plot_graph
from onshape_api.models.robot import Robot
from onshape_api.parse import (
    get_instances,
    get_mates_and_relations,
    get_occurences,
    get_parts,
    get_subassemblies,
)
from onshape_api.urdf import get_urdf_components
from onshape_api.utilities import LOGGER

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
DATA_DIRECTORY = "/../onshape_api/data"
ERRORED_ASSEMBLY = "errored_assembly.json"


def get_random_assembly(assembly_df: pd.DataFrame) -> dict:
    return assembly_df.sample().to_dict(orient="records")[0]


def get_random_urdf(data_path: str, client: Client):
    assembly_df = pd.read_parquet(data_path, engine="pyarrow")

    if os.path.exists(ERRORED_ASSEMBLY):
        assembly_dict = json.load(open(ERRORED_ASSEMBLY))
    else:
        assembly_dict = get_random_assembly(assembly_df)

    assembly, _ = client.get_assembly(
        did=assembly_dict["documentId"],
        wtype=assembly_dict["wtype"],
        wid=assembly_dict["workspaceId"],
        eid=assembly_dict["elementId"],
        with_meta_data=True,
    )

    assembly_robot_name = f"{assembly.document.name + '-' + assembly.name}"
    LOGGER.info(assembly.document.url)

    try:
        instances, id_to_name_map = get_instances(assembly)
        occurences = get_occurences(assembly, id_to_name_map)
        parts = get_parts(assembly, client, instances)
        subassemblies = get_subassemblies(assembly, instances)
        mates, relations = get_mates_and_relations(assembly, subassemblies, id_to_name_map)

        graph, root_node = create_graph(occurences=occurences, instances=instances, parts=parts, mates=mates)
        plot_graph(graph, f"{assembly_robot_name}.png")

        links, joints = get_urdf_components(
            assembly=assembly,
            graph=graph,
            root_node=root_node,
            parts=parts,
            mates=mates,
            relations=relations,
            client=client,
        )

        robot = Robot(name=f"{assembly_robot_name}", links=links, joints=joints)
        robot.save(f"{assembly_robot_name}.urdf")
        LOGGER.info(f"Onshape document: {assembly.document.url}")
        LOGGER.info(f"URDF saved to {os.path.abspath(f"{assembly_robot_name}.urdf")}")

    except Exception as e:
        LOGGER.warning(f"Error processing robot: {assembly_robot_name}")
        LOGGER.warning(e)
        LOGGER.warning(f"Onshape document: {assembly.document.url}")

        with open(ERRORED_ASSEMBLY, "w") as f:
            json.dump(assembly_dict, f, indent=4)


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    client = Client()
    get_random_urdf(f"{SCRIPT_DIRECTORY}{DATA_DIRECTORY}/assemblies.parquet", client)
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats("onshape.prof")
