import os

import onshape_api as opa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    client = opa.Client()
    # robot = https://cad.onshape.com/documents/a8f62e825e766a6512320ceb/w/b9099bcbdc92e6d6c810f0b7/e/f5b0475edd5ad0193d280fc4

    document = Document.from_url(
        "https://cad.onshape.com/documents/cf6b852d2c88d661ac2e17e8/w/c842455c29cc878dc48bdc68/e/b5e293d409dd0b88596181ef"
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
        use_user_defined_root=False,
    )
    opa.save_graph(graph, f"{assembly_robot_name}.png")

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
