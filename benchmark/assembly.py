import json
import os

import pandas as pd

from onshape_api.connect import Client
from onshape_api.graph import create_graph, show_graph
from onshape_api.models.assembly import Assembly
from onshape_api.models.document import Document
from onshape_api.models.robot import Robot
from onshape_api.parse import (
    get_instances,
    get_mates,
    get_occurences,
    get_parts,
    get_subassemblies,
)
from onshape_api.urdf import get_urdf_components
from onshape_api.utilities.helpers import get_random_file

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
JSON_DIRECTORY = "/../onshape_api/data/json"
PARQUET_FILE = "/../onshape_api/data/assemblies.parquet"

if __name__ == "__main__":
    client = Client()

    json_path = SCRIPT_DIRECTORY + JSON_DIRECTORY
    parquet_path = SCRIPT_DIRECTORY + PARQUET_FILE
    json_file_path, document_id = get_random_file(directory=json_path, file_extension=".json", count=1)
    assembly_df = pd.read_parquet(parquet_path, engine="pyarrow")

    json_data = json.load(open(json_file_path[0]))
    assembly = Assembly(**json_data)

    document_meta_data = client.get_document_metadata(document_id[0])
    document = Document(
        did=document_id[0], wtype="w", wid=document_meta_data.defaultWorkspace.id, eid=assembly_df.iloc[0]["elementId"]
    )

    assembly.document = document

    occurences = get_occurences(assembly)
    instances = get_instances(assembly)
    subassemblies = get_subassemblies(assembly, instances)
    parts = get_parts(assembly, client, instances)
    mates = get_mates(assembly)

    graph = create_graph(occurences=occurences, instances=instances, parts=parts, mates=mates, directed=False)
    show_graph(graph)

    if len(mates) == 0:
        raise ValueError("No mates found in assembly")

    links, joints = get_urdf_components(assembly, graph, parts, mates, client)

    robot = Robot(name=f"{document_meta_data.name}", links=links, joints=joints)
    robot.save(f"{document_meta_data.name}.urdf")
    print(f"onshape document: {document.url}")
