import cProfile
import json
import os
import pstats

from onshape_api.connect import Client
from onshape_api.graph import create_graph, save_graph
from onshape_api.models.assembly import Assembly
from onshape_api.models.document import Document, DocumentMetaData
from onshape_api.models.robot import Robot
from onshape_api.parse import (
    get_instances,
    get_mates,
    get_occurences,
    get_parts,
    get_subassemblies,
)
from onshape_api.urdf import get_urdf_components
from onshape_api.utilities import LOGGER
from onshape_api.utilities.helpers import get_random_files, get_sanitized_name

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
DATA_DIRECTORY = "/../onshape_api/data"


def main(checkpoint: int = 0):
    client = Client()

    if os.path.exists(f"checkpoint_document_{checkpoint}.json") and os.path.exists(
        f"checkpoint_assembly_{checkpoint}.json"
    ):
        with open(f"checkpoint_document_{checkpoint}.json") as f:
            document_meta_data = DocumentMetaData.model_validate_json(json.load(f))
        assembly = Assembly.model_validate_json(json.load(open(f"checkpoint_assembly_{checkpoint}.json")))

    else:
        json_path = SCRIPT_DIRECTORY + DATA_DIRECTORY + f"/assemblies_checkpoint_{checkpoint}_json"
        json_file_path, document_id = get_random_files(directory=json_path, file_extension=".json", count=1)

        json_data = json.load(open(json_file_path[0]))

        did = document_id[0].split("_")[0]
        eid = document_id[0].split("_")[1]

        document_meta_data = client.get_document_metadata(did)
        document_meta_data.name = get_sanitized_name(document_meta_data.name)

        document = Document(did=did, wtype="w", wid=document_meta_data.defaultWorkspace.id, eid=eid)
        assembly = Assembly(**json_data)
        assembly.document = document

    try:
        instances, id_to_name_map = get_instances(assembly)
        occurences = get_occurences(assembly, id_to_name_map)
        parts = get_parts(assembly, client, instances)
        subassemblies = get_subassemblies(assembly, instances)
        mates = get_mates(assembly, subassemblies, id_to_name_map)

        graph, root_node = create_graph(occurences=occurences, instances=instances, parts=parts, mates=mates)
        save_graph(graph, f"{document_meta_data.name}.png")

        links, joints = get_urdf_components(
            assembly=assembly, graph=graph, root_node=root_node, parts=parts, mates=mates, client=client
        )

        robot = Robot(name=f"{document_meta_data.name}", links=links, joints=joints)
        robot.save(f"{document_meta_data.name}.urdf")
        LOGGER.info(f"Onshape document: {assembly.document.url}")
        LOGGER.info(f"URDF saved to {os.path.abspath(f"{document_meta_data.name}.urdf")}")

    except Exception as e:
        LOGGER.warning(f"Error processing assembly: {document_meta_data.name}")
        LOGGER.warning(e)
        LOGGER.warning(f"Onshape document: {assembly.document.url}")

        with open(f"checkpoint_document_{checkpoint}.json", "w") as f:
            json.dump(document_meta_data.model_dump_json(), f)

        with open(f"checkpoint_assembly_{checkpoint}.json", "w") as f:
            json.dump(assembly.model_dump_json(), f)


if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    main()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats("onshape.prof")
