import json
import os

import onshape_api as opa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    client = opa.Client()

    json_path = SCRIPT_DIRECTORY + "/arbor_press.json"
    json_data = json.load(open(json_path))

    assembly = opa.Assembly.model_validate(json_data)
    document = client.get_document_metadata(assembly.rootAssembly.documentId)
    assembly.document = Document(
        did=assembly.rootAssembly.documentId,
        wtype=document.defaultWorkspace.type.shorthand,
        wid=document.defaultWorkspace.id,
        eid=assembly.rootAssembly.elementId,
        name=document.name,
    )

    opa.LOGGER.info(assembly.document.url)

    instances, id_to_name_map = opa.get_instances(assembly)
    occurences = opa.get_occurences(assembly, id_to_name_map)
    parts = opa.get_parts(assembly, client, instances)
    subassemblies = opa.get_subassemblies(assembly, instances)
    mates, relations = opa.get_mates_and_relations(assembly, subassemblies, id_to_name_map)

    graph, root_node = opa.create_graph(
        occurences=occurences,
        instances=instances,
        parts=parts,
        mates=mates,
    )
    opa.save_graph(graph, "robot.png")

    links, joints = opa.get_urdf_components(
        assembly=assembly,
        graph=graph,
        root_node=root_node,
        parts=parts,
        mates=mates,
        relations=relations,
        client=client,
    )

    robot = opa.Robot(name=document.name, links=links, joints=joints)
    robot.save("robot.urdf")
