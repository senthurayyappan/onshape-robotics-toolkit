import json
import os

from onshape_api.connect import Client
from onshape_api.graph import create_graph, show_graph
from onshape_api.models.assembly import Assembly
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
RELATIVE_DIRECTORY = "/../onshape_api/data/json"

if __name__ == "__main__":
    client = Client()
    json_path = SCRIPT_DIRECTORY + RELATIVE_DIRECTORY
    json_file = get_random_file(directory=json_path, file_extension=".json", count=1)

    json_data = json.load(open(json_file[0]))
    assembly = Assembly(**json_data)

    occurences = get_occurences(assembly)
    instances = get_instances(assembly)
    subassemblies = get_subassemblies(assembly, instances)
    parts = get_parts(assembly, instances)
    mates = get_mates(assembly)

    graph = create_graph(occurences=occurences, instances=instances, parts=parts, mates=mates, directed=False)
    show_graph(graph)

    links, joints = get_urdf_components(assembly, graph, parts, mates, client)

    robot = Robot(name="bike", links=links, joints=joints)
    robot.save("bike.urdf")
