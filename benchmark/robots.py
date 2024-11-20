import os

import onshape_api as opa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    client = opa.Client()
    # robot = https://cad.onshape.com/documents/a8f62e825e766a6512320ceb/w/b9099bcbdc92e6d6c810f0b7/e/f5b0475edd5ad0193d280fc4
    # robot dog = https://cad.onshape.com/documents/d0223bce364d259e80667122/w/b52c33333c8553dce379aac6/e/57728d0a8bc87b7b065e43be
    # simple robot dog = https://cad.onshape.com/documents/64d7b47821f3f5c91e3cd128/w/051d83c286bca38e8952dd84/e/ba886678bddf9de9c01723c8

    # test-nested-subassemblies = https://cad.onshape.com/documents/8c7a1c45e27a40a5b6e44d92/w/9c50078d1ac7106985359fe8/e/8c0e0762c95eb6e8b2f4b1f1

    document = Document.from_url(
        "https://cad.onshape.com/documents/8c7a1c45e27a40a5b6e44d92/w/9c50078d1ac7106985359fe8/e/8c0e0762c95eb6e8b2f4b1f1"
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
    opa.save_model_as_json(assembly, f"{assembly_robot_name}.json")

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
    opa.plot_graph(graph)

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
