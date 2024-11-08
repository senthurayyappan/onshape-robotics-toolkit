import json
import os
import re
from functools import partial

import pandas as pd

from onshape_api.connect import Client
from onshape_api.models import Assembly
from onshape_api.models.document import generate_url
from onshape_api.models.element import Element, ElementType
from onshape_api.utilities import LOGGER

AUTOMATE_ASSEMBLYID_PATTERN = r"(?P<documentId>\w{24})_(?P<documentMicroversion>\w{24})_(?P<elementId>\w{24})"


def extract_ids(assembly_id):
    match = re.match(AUTOMATE_ASSEMBLYID_PATTERN, assembly_id)
    if match:
        return match.groupdict()
    else:
        return {"documentId": None, "documentMicroversion": None, "elementId": None}


def raise_document_not_exist_error(documentId):
    raise ValueError(f"Document does not exist: {documentId}")


def get_assembly_data(assembly_id: str, client: Client):
    try:
        ids = extract_ids(assembly_id)
        document = client.get_document_metadata(ids["documentId"])

        if document is None:
            raise_document_not_exist_error(ids["documentId"])

        elements: list[Element] = client.get_elements(
            did=document.id, wtype=document.defaultWorkspace.type.shorthand, wid=document.defaultWorkspace.id
        )
        assembly_ids = [element.id for element in elements.values() if element.elementType == ElementType.ASSEMBLY]

        ids["elementId"] = assembly_ids
        ids["wtype"] = document.defaultWorkspace.type.shorthand
        ids["workspaceId"] = document.defaultWorkspace.id

        LOGGER.info(f"Assembly data retrieved for element: {ids['elementId']}")

    except Exception as e:
        LOGGER.warning(f"Error getting assembly data for {assembly_id}")
        LOGGER.warning(e)
        ids = {"documentId": None, "documentMicroversion": None, "elementId": None, "wtype": None, "workspaceId": None}

    return ids


def get_assembly_df(automate_assembly_df: pd.DataFrame, client: Client) -> pd.DataFrame:
    """
    Automate assembly data format:
        {
            "assemblyId":"000355ca65fdcbb0e3d825e6_811a5312224ae67ce5b1e180_4bd8ec79e9921e03b989f893_default",
            "n_subassemblies":1,
            "n_parts":11,
            "n_parasolid":11,
            "n_parasolid_errors":0,
            "n_step":11,
            "n_occurrences":11,
            "n_mates":10,
            "n_ps_mates":10,
            "n_step_mates":10,
            "n_groups":0,
            "n_relations":0,
            "is_subassembly":false
        }
    """
    _get_assembly_data = partial(get_assembly_data, client=client)
    assembly_df = automate_assembly_df["assemblyId"].apply(_get_assembly_data).apply(pd.Series)
    return assembly_df


def save_all_jsons(client: Client):
    if not os.path.exists("assemblies.parquet"):
        automate_assembly_df = pd.read_parquet("automate_assemblies.parquet", engine="pyarrow")
        assembly_df = get_assembly_df(automate_assembly_df, client=client)
        assembly_df.to_parquet("assemblies.parquet", engine="pyarrow")
    else:
        assembly_df = pd.read_parquet("assemblies.parquet", engine="pyarrow")

    json_dir = "json"
    os.makedirs(json_dir, exist_ok=True)

    for _, row in assembly_df.iterrows():
        try:
            for element_id in row["elementId"]:
                _, assembly_json = client.get_assembly(
                    did=row["documentId"],
                    wtype=row["wtype"],
                    wid=row["workspaceId"],
                    eid=element_id,
                    log_response=False,
                )

                json_file_path = os.path.join(json_dir, f"{row['documentId']}_{element_id}.json")
                with open(json_file_path, "w") as json_file:
                    json.dump(assembly_json, json_file, indent=4)

                LOGGER.info(f"Assembly JSON saved to {json_file_path}")

        except Exception as e:
            LOGGER.warning(f"Error saving assembly JSON: {os.path.abspath(json_file_path)}")
            document_url = generate_url(row["documentId"], row["wtype"], row["workspaceId"], element_id)
            LOGGER.warning(f"Onshape document: {document_url}")
            LOGGER.warning(f"Assembly JSON: {assembly_json}")
            LOGGER.warning(f"Element ID: {row['elementId']}")
            LOGGER.warning(e)

            break


def validate_assembly_json(json_file_path: str):
    with open(json_file_path) as json_file:
        assembly_json = json.load(json_file)

    return Assembly.model_validate(assembly_json)


if __name__ == "__main__":
    client = Client()
    save_all_jsons(client)
