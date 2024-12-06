import os

import onshape_api as osa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    client = osa.Client()
    # robot = https://cad.onshape.com/documents/a8f62e825e766a6512320ceb/w/b9099bcbdc92e6d6c810f0b7/e/f5b0475edd5ad0193d280fc4
    # robot dog = https://cad.onshape.com/documents/d0223bce364d259e80667122/w/b52c33333c8553dce379aac6/e/57728d0a8bc87b7b065e43be
    # simple robot dog = https://cad.onshape.com/documents/64d7b47821f3f5c91e3cd128/w/051d83c286bca38e8952dd84/e/ba886678bddf9de9c01723c8

    # test-nested-subassemblies = https://cad.onshape.com/documents/8c7a1c45e27a40a5b6e44d92/w/9c50078d1ac7106985359fe8/e/8c0e0762c95eb6e8b2f4b1f1
    # test-transformations = https://cad.onshape.com/documents/9c982cc66e2d3357ecf31371/w/21b699e5966180f4906fb6d1/e/1a44468a497fb472bc80d884
    # test-nested-mategroups = https://cad.onshape.com/documents/12124a46ebda8f31ccfe8c8f/w/820e30e034d40fc174232361/e/54c32b7d2abd32b9bf6d9641
    # ballbot = https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29

    document = Document.from_url(
        "https://cad.onshape.com/documents/12124a46ebda8f31ccfe8c8f/w/820e30e034d40fc174232361/e/54c32b7d2abd32b9bf6d9641"
    )
    assembly, _ = client.get_assembly(
        did=document.did,
        wtype=document.wtype,
        wid=document.wid,
        eid=document.eid,
    )

    osa.LOGGER.info(assembly.document.url)
    assembly_robot_name = f"{assembly.document.name + '-' + assembly.name}"
    osa.save_model_as_json(assembly, f"{assembly_robot_name}.json")

    instances, occurrences, id_to_name_map = osa.get_instances(assembly)
    subassemblies, rigid_subassemblies = osa.get_subassemblies(assembly, client, instances)
    parts = osa.get_parts(assembly, rigid_subassemblies, client, instances)

    mates, relations = osa.get_mates_and_relations(assembly, subassemblies, rigid_subassemblies, id_to_name_map, parts)

    graph, root_node = osa.create_graph(
        occurrences=occurrences,
        instances=instances,
        parts=parts,
        mates=mates,
        use_user_defined_root=True,
    )
    osa.plot_graph(graph)

    links, joints = osa.get_urdf_components(
        assembly=assembly,
        graph=graph,
        root_node=root_node,
        parts=parts,
        mates=mates,
        relations=relations,
        client=client,
    )

    robot = osa.Robot(name=assembly_robot_name, links=links, joints=joints)
    robot.save(f"{assembly_robot_name}.urdf")
