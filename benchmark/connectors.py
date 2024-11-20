import os

import onshape_api as opa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    client = opa.Client()

    # connectors witch cycle: https://cad.onshape.com/documents/8df4a8934dea6cc8a51a6f85/w/5473d6310f998d61ffe1045e/e/dcf8d3ded2234a1bea3856ba
    # simple connectors: https://cad.onshape.com/documents/2e35965a561baafef08b14bc/w/967b9a19ea54f3cb2703ba2d/e/ebe351dafa0a477efb87912e
    # T joint: https://cad.onshape.com/documents/7481cfb61a62765f39b1f8b6/w/7c3a25b7fe7637d71f04f632/e/fbf64c254c6cde3d16c91250
    document = Document.from_url(
        "https://cad.onshape.com/documents/7481cfb61a62765f39b1f8b6/w/7c3a25b7fe7637d71f04f632/e/fbf64c254c6cde3d16c91250"
    )
    assembly, _ = client.get_assembly(
        did=document.did,
        wtype=document.wtype,
        wid=document.wid,
        eid=document.eid,
        with_meta_data=True,
    )

    opa.LOGGER.info(assembly.document.url)
    assembly_robot_name = f"{assembly.document.name + '-' + assembly.name}"

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
        directed=True,
        use_user_defined_root=True,
    )
    opa.plot_graph(graph, f"{assembly_robot_name}.png")

    links, joints = opa.get_urdf_components(
        assembly=assembly,
        graph=graph,
        root_node=root_node,
        parts=parts,
        mates=mates,
        relations=relations,
        client=client,
    )

    robot = opa.Robot(name=assembly_robot_name, links=links, joints=joints)
    robot.save(f"{assembly_robot_name}.urdf")
