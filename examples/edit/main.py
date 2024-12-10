from onshape_api.connect import Client
from onshape_api.graph import create_graph, plot_graph
from onshape_api.log import LOGGER, LogLevel
from onshape_api.models.document import Document
from onshape_api.parse import (
    get_instances,
    get_mates_and_relations,
    get_parts,
    get_subassemblies,
)
from onshape_api.robot import Robot
from onshape_api.urdf import get_urdf_components

if __name__ == "__main__":
    LOGGER.set_file_name("edit.log")
    LOGGER.set_stream_level(LogLevel.INFO)

    client = Client()
    doc = Document.from_url(
        url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
    )

    elements = client.get_elements(doc.did, doc.wtype, doc.wid)
    variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

    variables["wheelDiameter"].expression = "180 mm"
    variables["wheelThickness"].expression = "71 mm"
    variables["forkAngle"].expression = "20 deg"

    client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
    assembly = client.get_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id)

    instances, occurrences, id_to_name_map = get_instances(assembly)

    subassemblies, rigid_subassemblies = get_subassemblies(assembly, client, instances)
    parts = get_parts(assembly, rigid_subassemblies, client, instances)

    mates, relations = get_mates_and_relations(assembly, subassemblies, rigid_subassemblies, id_to_name_map, parts)

    graph, root_node = create_graph(occurrences=occurrences, instances=instances, parts=parts, mates=mates)
    plot_graph(graph, "bike.png")

    links, joints, assets = get_urdf_components(assembly, graph, root_node, parts, mates, relations, client)
    robot = Robot(name="bike", links=links, joints=joints, assets=assets)
    robot.save()
