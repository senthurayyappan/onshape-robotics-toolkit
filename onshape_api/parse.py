"""
This module contains functions that provide a way to traverse the assembly structure, extract information about parts,
subassemblies, instances, and mates, and generate a hierarchical representation of the assembly.

"""

import asyncio
import os
from typing import Optional, Union

import numpy as np

from onshape_api.connect import Client
from onshape_api.log import LOGGER
from onshape_api.models.assembly import (
    Assembly,
    AssemblyFeatureType,
    AssemblyInstance,
    InstanceType,
    MatedCS,
    MateFeatureData,
    MateRelationFeatureData,
    Occurrence,
    Part,
    PartInstance,
    RelationType,
    RootAssembly,
    SubAssembly,
)
from onshape_api.models.document import WorkspaceType
from onshape_api.utilities.helpers import get_sanitized_name

os.environ["TCL_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ["TK_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"

SUBASSEMBLY_JOINER = "-SUB-"
MATE_JOINER = "_to_"

CHILD = 0
PARENT = 1

RELATION_CHILD = 1
RELATION_PARENT = 0


# TODO: get_mate_connectors method to parse part mate connectors that may be useful to someone
async def traverse_instances_async(
    root: Union[RootAssembly, SubAssembly],
    prefix: str,
    current_depth: int,
    max_depth: int,
    assembly: Assembly,
    id_to_name_map: dict[str, str],
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]],
) -> None:
    """
    Asynchronously traverse the assembly structure to get instances.
    """
    if current_depth >= max_depth:
        LOGGER.debug(f"Max depth {max_depth} reached. Stopping traversal at depth {current_depth}.")
        return

    for instance in root.instances:
        sanitized_name = get_sanitized_name(instance.name)
        LOGGER.debug(f"Parsing instance: {sanitized_name}")
        instance_id = f"{prefix}{SUBASSEMBLY_JOINER}{sanitized_name}" if prefix else sanitized_name
        id_to_name_map[instance.id] = sanitized_name
        instance_map[instance_id] = instance

        # Handle subassemblies concurrently
        if instance.type == InstanceType.ASSEMBLY:
            tasks = [
                traverse_instances_async(
                    sub_assembly, instance_id, current_depth + 1, max_depth, assembly, id_to_name_map, instance_map
                )
                for sub_assembly in assembly.subAssemblies
                if sub_assembly.uid == instance.uid
            ]
            await asyncio.gather(*tasks)


def get_instances(
    assembly: Assembly, max_depth: int = 5
) -> tuple[dict[str, Union[PartInstance, AssemblyInstance]], dict[str, Occurrence], dict[str, str]]:
    """
    Optimized synchronous wrapper for `get_instances`.
    """
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]] = {}
    id_to_name_map: dict[str, str] = {}
    asyncio.run(
        traverse_instances_async(
            assembly.rootAssembly,
            "",
            0,
            max_depth,
            assembly,
            id_to_name_map,
            instance_map,
        )
    )
    occurrence_map = get_occurrences(assembly, id_to_name_map, max_depth)
    return instance_map, occurrence_map, id_to_name_map


def get_instances_sync(
    assembly: Assembly, max_depth: int = 5
) -> tuple[dict[str, Union[PartInstance, AssemblyInstance]], dict[str, Occurrence], dict[str, str]]:
    """
    Get instances and their sanitized names from an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting instances.
        max_depth: Maximum depth to traverse in the assembly hierarchy. Default is 5

    Returns:
        A tuple containing:
        - A dictionary mapping instance IDs to their corresponding instances.
        - A dictionary mapping instance IDs to their sanitized names.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_instances(assembly, max_depth=2)
        (
            {
                "part1": PartInstance(...),
                "subassembly1": AssemblyInstance(...),
            },
            {
                "part1": "part1",
                "subassembly1": "subassembly1",
            }
        )
    """

    def traverse_instances(
        root: Union[RootAssembly, SubAssembly], prefix: str = "", current_depth: int = 0
    ) -> tuple[dict[str, Union[PartInstance, AssemblyInstance]], dict[str, str]]:
        """
        Traverse the assembly structure to get instances.

        Args:
            root: Root assembly or subassembly object to traverse.
            prefix: Prefix for the instance ID.
            current_depth: Current depth in the assembly hierarchy.

        Returns:
            A tuple containing:
            - A dictionary mapping instance IDs to their corresponding instances.
            - A dictionary mapping instance IDs to their sanitized names.
        """
        instance_map = {}
        id_to_name_map = {}

        # Stop traversing if the maximum depth is reached
        if current_depth >= max_depth:
            LOGGER.debug(f"Max depth {max_depth} reached. Stopping traversal at depth {current_depth}.")
            return instance_map, id_to_name_map

        for instance in root.instances:
            sanitized_name = get_sanitized_name(instance.name)
            LOGGER.debug(f"Parsing instance: {sanitized_name}")
            instance_id = f"{prefix}{SUBASSEMBLY_JOINER}{sanitized_name}" if prefix else sanitized_name
            id_to_name_map[instance.id] = sanitized_name
            instance_map[instance_id] = instance

            # Recursively process sub-assemblies if applicable
            if instance.type == InstanceType.ASSEMBLY:
                for sub_assembly in assembly.subAssemblies:
                    if sub_assembly.uid == instance.uid:
                        sub_instance_map, sub_id_to_name_map = traverse_instances(
                            sub_assembly, instance_id, current_depth + 1
                        )
                        instance_map.update(sub_instance_map)
                        id_to_name_map.update(sub_id_to_name_map)

        return instance_map, id_to_name_map

    instance_map, id_to_name_map = traverse_instances(assembly.rootAssembly)
    # return occurrences internally as it relies on max_depth
    occurrence_map = get_occurrences(assembly, id_to_name_map, max_depth)

    return instance_map, occurrence_map, id_to_name_map


def get_occurrences(assembly: Assembly, id_to_name_map: dict[str, str], max_depth: int = 5) -> dict[str, Occurrence]:
    """
    Optimized occurrences fetching using comprehensions.
    """
    return {
        SUBASSEMBLY_JOINER.join([
            id_to_name_map[path] for path in occurrence.path if path in id_to_name_map
        ]): occurrence
        for occurrence in assembly.rootAssembly.occurrences
        if len(occurrence.path) <= max_depth
    }


async def fetch_rigid_subassemblies_async(
    subassembly: SubAssembly, key: str, client: Client, rigid_subassembly_map: dict[str, RootAssembly]
):
    """
    Fetch rigid subassemblies asynchronously.
    """
    try:
        rigid_subassembly_map[key] = await asyncio.to_thread(
            client.get_root_assembly,
            did=subassembly.documentId,
            wtype=WorkspaceType.M.value,
            wid=subassembly.documentMicroversion,
            eid=subassembly.elementId,
            with_mass_properties=True,
            log_response=False,
        )
    except Exception as e:
        LOGGER.error(f"Failed to fetch rigid subassembly for {key}: {e}")


async def get_subassemblies_async(
    assembly: Assembly,
    client: Client,
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]],
) -> tuple[dict[str, SubAssembly], dict[str, RootAssembly]]:
    """
    Asynchronously fetch subassemblies.
    """
    subassembly_map: dict[str, SubAssembly] = {}
    rigid_subassembly_map: dict[str, RootAssembly] = {}

    # Group by UID
    subassembly_instance_map = {
        instance.uid: [] for instance in instance_map.values() if instance.type == InstanceType.ASSEMBLY
    }
    for key, instance in instance_map.items():
        if instance.type == InstanceType.ASSEMBLY:
            subassembly_instance_map[instance.uid].append(key)

    # Process subassemblies concurrently
    tasks = []
    for subassembly in assembly.subAssemblies:
        uid = subassembly.uid
        if uid in subassembly_instance_map:
            is_rigid = len(subassembly.features) == 0 or all(
                feature.featureType == AssemblyFeatureType.MATEGROUP for feature in subassembly.features
            )
            for key in subassembly_instance_map[uid]:
                if is_rigid:
                    tasks.append(fetch_rigid_subassemblies_async(subassembly, key, client, rigid_subassembly_map))
                else:
                    subassembly_map[key] = subassembly

    await asyncio.gather(*tasks)
    return subassembly_map, rigid_subassembly_map


def get_subassemblies(
    assembly: Assembly,
    client: Client,
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]],
) -> tuple[dict[str, SubAssembly], dict[str, RootAssembly]]:
    """
    Synchronous wrapper for `get_subassemblies_async`.
    """
    return asyncio.run(get_subassemblies_async(assembly, client, instance_map))


async def fetch_mass_properties_async(
    part: Part,
    key: str,
    client: Client,
    rigid_subassembly_map: dict[str, RootAssembly],
    part_map: dict[str, Part],
):
    """
    Asynchronously fetch mass properties for a part.

    Args:
        part: The part for which to fetch mass properties.
        key: The instance key associated with the part.
        client: The Onshape client object.
        rigid_subassembly_map: Mapping of instance IDs to rigid subassemblies.
        part_map: The dictionary to store fetched parts.
    """
    if key.split(SUBASSEMBLY_JOINER)[0] not in rigid_subassembly_map:
        try:
            LOGGER.info(f"Fetching mass properties for part: {part.documentVersion}, {part.partId}")
            part.MassProperty = await asyncio.to_thread(
                client.get_mass_property,
                did=part.documentId,
                wtype=WorkspaceType.M.value,
                wid=part.documentMicroversion,
                eid=part.elementId,
                partID=part.partId,
            )
        except Exception as e:
            LOGGER.error(f"Failed to fetch mass properties for part {part.partId}: {e}")

    part_map[key] = part


async def get_parts_async(
    assembly: Assembly,
    rigid_subassembly_map: dict[str, RootAssembly],
    client: Client,
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]],
) -> dict[str, Part]:
    """
    Asynchronously get parts of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting parts.
        rigid_subassembly_map: Mapping of instance IDs to rigid subassemblies.
        client: The Onshape client object.
        instance_map: Mapping of instance IDs to their corresponding instances.

    Returns:
        A dictionary mapping part IDs to their corresponding part objects.
    """
    part_instance_map: dict[str, list[str]] = {}
    part_map: dict[str, Part] = {}

    for key, instance in instance_map.items():
        if instance.type == InstanceType.PART:
            part_instance_map.setdefault(instance.uid, []).append(key)

    tasks = []
    for part in assembly.parts:
        if part.uid in part_instance_map:
            for key in part_instance_map[part.uid]:
                tasks.append(fetch_mass_properties_async(part, key, client, rigid_subassembly_map, part_map))

    await asyncio.gather(*tasks)

    return part_map


def get_parts(
    assembly: Assembly,
    rigid_subassembly_map: dict[str, RootAssembly],
    client: Client,
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]],
) -> dict[str, Part]:
    """
    Get parts of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting parts.
        rigid_subassembly_map: Mapping of instance IDs to rigid subassemblies.
        client: The Onshape client object to use for sending API requests.
        instance_map: Mapping of instance IDs to their corresponding instances.

    Returns:
        A dictionary mapping part IDs to their corresponding part objects.
    """
    return asyncio.run(get_parts_async(assembly, rigid_subassembly_map, client, instance_map))


def get_occurrence_name(occurrences: list[str], subassembly_prefix: Optional[str] = None) -> str:
    """
    Get the mapping name for an occurrence path.

    Args:
        occurrences: Occurrence path.
        subassembly_prefix: Prefix for the subassembly.

    Returns:
        The mapping name.

    Examples:
        >>> get_occurrence_name(["subassembly1", "part1"], "subassembly1")
        "subassembly1-SUB-part1"

        >>> get_occurrence_name(["part1"], "subassembly1")
        "subassembly1-SUB-part1"
    """
    prefix = f"{subassembly_prefix}{SUBASSEMBLY_JOINER}" if subassembly_prefix else ""
    return f"{prefix}{SUBASSEMBLY_JOINER.join(occurrences)}"


def join_mate_occurrences(parent: list[str], child: list[str], prefix: Optional[str] = None) -> str:
    """
    Join two occurrence paths with a mate joiner.

    Args:
        parent: Occurrence path of the parent entity.
        child: Occurrence path of the child entity.
        prefix: Prefix to add to the occurrence path.

    Returns:
        The joined occurrence path.

    Examples:
        >>> join_mate_occurrences(["subassembly1", "part1"], ["subassembly2"])
        "subassembly1-SUB-part1-MATE-subassembly2"

        >>> join_mate_occurrences(["part1"], ["part2"])
        "part1-MATE-part2"
    """
    parent_occurrence = get_occurrence_name(parent, prefix)
    child_occurrence = get_occurrence_name(child, prefix)
    return f"{parent_occurrence}{MATE_JOINER}{child_occurrence}"


async def build_rigid_subassembly_occurrence_map(
    rigid_subassembly_map: dict[str, RootAssembly], id_to_name_map: dict[str, str], parts: dict[str, Part]
) -> dict[str, dict[str, Occurrence]]:
    """
    Asynchronously build a map of rigid subassembly occurrences.
    """
    occurrence_map: dict[str, dict[str, Occurrence]] = {}
    for assembly_key, rigid_subassembly in rigid_subassembly_map.items():
        sub_occurrences: dict[str, Occurrence] = {}
        for occurrence in rigid_subassembly.occurrences:
            try:
                occurrence_path = [id_to_name_map[path] for path in occurrence.path]
                sub_occurrences[SUBASSEMBLY_JOINER.join(occurrence_path)] = occurrence
            except KeyError:
                LOGGER.warning(f"Occurrence path {occurrence.path} not found")

        # Populate parts data
        parts[assembly_key] = Part(
            isStandardContent=False,
            fullConfiguration=rigid_subassembly.fullConfiguration,
            configuration=rigid_subassembly.configuration,
            documentId=rigid_subassembly.documentId,
            elementId=rigid_subassembly.elementId,
            documentMicroversion=rigid_subassembly.documentMicroversion,
            documentVersion="",
            partId="",
            bodyType="",
            MassProperty=rigid_subassembly.MassProperty,
            isRigidAssembly=True,
            rigidAssemblyWorkspaceId=rigid_subassembly.documentMetaData.defaultWorkspace.id,
            rigidAssemblyToPartTF={},
        )
        occurrence_map[assembly_key] = sub_occurrences

    return occurrence_map


async def process_features_async(  # noqa: C901
    features: list,
    parts: dict[str, Part],
    id_to_name_map: dict[str, str],
    rigid_subassembly_occurrence_map: dict[str, dict[str, Occurrence]],
    rigid_subassembly_map: dict[str, RootAssembly],
    subassembly_prefix: Optional[str],
) -> tuple[dict[str, MateFeatureData], dict[str, MateRelationFeatureData]]:
    """
    Process assembly features asynchronously.
    """
    mates_map: dict[str, MateFeatureData] = {}
    relations_map: dict[str, MateRelationFeatureData] = {}

    for feature in features:
        feature.featureData.id = feature.id

        if feature.suppressed:
            continue

        if feature.featureType == AssemblyFeatureType.MATE:
            if len(feature.featureData.matedEntities) < 2:
                LOGGER.warning(f"Invalid mate feature: {feature}")
                continue

            try:
                child_occurrences = [
                    id_to_name_map[path] for path in feature.featureData.matedEntities[CHILD].matedOccurrence
                ]
                parent_occurrences = [
                    id_to_name_map[path] for path in feature.featureData.matedEntities[PARENT].matedOccurrence
                ]
            except KeyError as e:
                LOGGER.warning(e)
                LOGGER.warning(f"Key not found in {id_to_name_map.keys()}")
                continue

            # Handle rigid subassemblies
            if parent_occurrences[0] in rigid_subassembly_map:
                _occurrence = rigid_subassembly_occurrence_map[parent_occurrences[0]].get(parent_occurrences[1])
                if _occurrence:
                    parent_parentCS = MatedCS.from_tf(np.matrix(_occurrence.transform).reshape(4, 4))
                    parts[parent_occurrences[0]].rigidAssemblyToPartTF[parent_occurrences[1]] = parent_parentCS.part_tf
                    feature.featureData.matedEntities[PARENT].parentCS = parent_parentCS
                parent_occurrences = [parent_occurrences[0]]

            if child_occurrences[0] in rigid_subassembly_map:
                _occurrence = rigid_subassembly_occurrence_map[child_occurrences[0]].get(child_occurrences[1])
                if _occurrence:
                    child_parentCS = MatedCS.from_tf(np.matrix(_occurrence.transform).reshape(4, 4))
                    parts[child_occurrences[0]].rigidAssemblyToPartTF[child_occurrences[1]] = child_parentCS.part_tf
                    feature.featureData.matedEntities[CHILD].parentCS = child_parentCS
                child_occurrences = [child_occurrences[0]]

            mates_map[
                join_mate_occurrences(
                    parent=parent_occurrences,
                    child=child_occurrences,
                    prefix=subassembly_prefix,
                )
            ] = feature.featureData

        elif feature.featureType == AssemblyFeatureType.MATERELATION:
            if feature.featureData.relationType == RelationType.SCREW:
                child_joint_id = feature.featureData.mates[0].featureId
            else:
                child_joint_id = feature.featureData.mates[RELATION_CHILD].featureId

            relations_map[child_joint_id] = feature.featureData

    return mates_map, relations_map


async def get_mates_and_relations_async(
    assembly: Assembly,
    subassembly_map: dict[str, SubAssembly],
    rigid_subassembly_map: dict[str, RootAssembly],
    id_to_name_map: dict[str, str],
    parts: dict[str, Part],
) -> tuple[dict[str, MateFeatureData], dict[str, MateRelationFeatureData]]:
    """
    Asynchronously get mates and relations.
    """
    rigid_subassembly_occurrence_map = await build_rigid_subassembly_occurrence_map(
        rigid_subassembly_map, id_to_name_map, parts
    )

    mates_map, relations_map = await process_features_async(
        assembly.rootAssembly.features,
        parts,
        id_to_name_map,
        rigid_subassembly_occurrence_map,
        rigid_subassembly_map,
        None,
    )

    for key, subassembly in subassembly_map.items():
        sub_mates, sub_relations = await process_features_async(
            subassembly.features, parts, id_to_name_map, rigid_subassembly_occurrence_map, rigid_subassembly_map, key
        )
        mates_map.update(sub_mates)
        relations_map.update(sub_relations)

    return mates_map, relations_map


def get_mates_and_relations(
    assembly: Assembly,
    subassembly_map: dict[str, SubAssembly],
    rigid_subassembly_map: dict[str, RootAssembly],
    id_to_name_map: dict[str, str],
    parts: dict[str, Part],
) -> tuple[dict[str, MateFeatureData], dict[str, MateRelationFeatureData]]:
    """
    Synchronous wrapper for `get_mates_and_relations_async`.
    """
    return asyncio.run(
        get_mates_and_relations_async(assembly, subassembly_map, rigid_subassembly_map, id_to_name_map, parts)
    )
