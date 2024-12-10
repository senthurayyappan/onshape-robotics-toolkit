import os

from onshape_api.connect import Client
from onshape_api.graph import create_graph, plot_graph
from onshape_api.log import LOGGER, LogLevel
from onshape_api.models.document import Document
from onshape_api.parse import get_instances, get_mates_and_relations, get_parts, get_subassemblies
from onshape_api.robot import Robot
from onshape_api.urdf import get_urdf_components
from onshape_api.utilities.helpers import save_model_as_json

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    LOGGER.set_file_name("export.log")
    LOGGER.set_stream_level(LogLevel.INFO)
    client = Client()

    document = Document.from_url(
        "https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29"
    )
    assembly = client.get_assembly(
        did=document.did,
        wtype=document.wtype,
        wid=document.wid,
        eid=document.eid,
    )

    LOGGER.info(assembly.document.url)
    assembly_robot_name = f"{assembly.document.name + '-' + assembly.name}"
    save_model_as_json(assembly, f"{assembly_robot_name}.json")

    instances, occurrences, id_to_name_map = get_instances(assembly)
    subassemblies, rigid_subassemblies = get_subassemblies(assembly, client, instances)

    parts = get_parts(assembly, rigid_subassemblies, client, instances)
    mates, relations = get_mates_and_relations(assembly, subassemblies, rigid_subassemblies, id_to_name_map, parts)

    graph, root_node = create_graph(
        occurrences=occurrences,
        instances=instances,
        parts=parts,
        mates=mates,
        use_user_defined_root=False,
    )
    plot_graph(graph, f"{assembly_robot_name}.png")

    links, joints, assets = get_urdf_components(
        assembly=assembly,
        graph=graph,
        root_node=root_node,
        parts=parts,
        mates=mates,
        relations=relations,
        client=client,
    )

    robot = Robot(name=assembly_robot_name, links=links, joints=joints, assets=assets)
    robot.save()
