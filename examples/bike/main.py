import onshape_api as osa
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

# Initialize the client with the constructed path
client = osa.Client()
doc = osa.Document.from_url(
    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
)

elements = client.get_elements(doc.did, doc.wtype, doc.wid)
variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

variables["wheelDiameter"].expression = "180 mm"
variables["wheelThickness"].expression = "71 mm"
variables["forkAngle"].expression = "20 deg"

client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
assembly, _ = client.get_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id)

instances, id_to_name_map = get_instances(assembly)
occurences = get_occurences(assembly, id_to_name_map)
subassemblies = get_subassemblies(assembly, instances)
parts = get_parts(assembly, client, instances)
mates, relations = get_mates_and_relations(assembly, subassembly_map=subassemblies, id_to_name_map=id_to_name_map)

graph, root_node = create_graph(occurences=occurences, instances=instances, parts=parts, mates=mates)
plot_graph(graph, "bike.png")

links, joints = get_urdf_components(assembly, graph, root_node, parts, mates, relations, client)
robot = Robot(name="bike", links=links, joints=joints)
robot.save("bike.urdf")
