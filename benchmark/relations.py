import os

import onshape_api as opa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    client = opa.Client()

    # arbor press: https://cad.onshape.com/documents/00fdecd70b9459267a70825e/w/5b8859e00b5d129724548da1/e/8bb8553f756c40770e11d5b4
    # all relations: https://cad.onshape.com/documents/803be93f774b2e9ca86c62ee/w/eaea71496511e472d717774f/e/55d451923bedd28a364efb84
    # gears: https://cad.onshape.com/documents/8df4a8934dea6cc8a51a6f85/w/5473d6310f998d61ffe1045e/e/dcf8d3ded2234a1bea3856ba

    document = Document.from_url(
        "https://cad.onshape.com/documents/00fdecd70b9459267a70825e/w/5b8859e00b5d129724548da1/e/8bb8553f756c40770e11d5b4"
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
