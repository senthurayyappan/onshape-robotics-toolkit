import json
import os
import re

import pandas as pd

from onshape_api.connect import Client
from onshape_api.models import Assembly

AUTOMATE_ASSEMBLYID_PATTERN = r"(?P<documentId>\w{24})_(?P<documentMicroversion>\w{24})_(?P<elementId>\w{24})"


def extract_ids(assembly_id):
    match = re.match(AUTOMATE_ASSEMBLYID_PATTERN, assembly_id)
    if match:
        return match.groupdict()
    else:
        return {"documentId": None, "documentMicroversion": None, "elementId": None}


def get_assembly_df(automate_assembly_df):
    assembly_df = automate_assembly_df["assemblyId"].apply(extract_ids).apply(pd.Series)
    return assembly_df


def save_all_jsons(client: Client):
    if not os.path.exists("assemblies.parquet"):
        automate_assembly_df = pd.read_parquet("automate_assemblies.parquet", engine="pyarrow")
        assembly_df = get_assembly_df(automate_assembly_df)
        assembly_df.to_parquet("assemblies.parquet", engine="pyarrow")
    else:
        assembly_df = pd.read_parquet("assemblies.parquet", engine="pyarrow")

    print(assembly_df.head())

    document = client.get_document_metadata(assembly_df.iloc[0]["documentId"])
    assembly, assembly_json = client.get_assembly(
        assembly_df.iloc[0]["documentId"], "w", document.defaultWorkspace.id, assembly_df.iloc[0]["elementId"]
    )

    json_dir = "json"
    os.makedirs(json_dir, exist_ok=True)

    for index, row in assembly_df.iterrows():
        try:
            document = client.get_document_metadata(row["documentId"])
            assembly, assembly_json = client.get_assembly(
                row["documentId"], "w", document.defaultWorkspace.id, row["elementId"]
            )

            json_file_path = os.path.join(json_dir, f"{row['documentId']}.json")
            with open(json_file_path, "w") as json_file:
                json.dump(assembly_json, json_file, indent=4)

            print(f"Assembly JSON saved to {json_file_path}")
        except Exception as e:
            print(f"An error occurred for row {index}: {e}")


if __name__ == "__main__":
    client = Client()
    # save_all_jsons(client)

    json_file_path = "mate_relations.json"
    with open(json_file_path) as json_file:
        assembly_json = json.load(json_file)

    assembly = Assembly.model_validate(assembly_json)
