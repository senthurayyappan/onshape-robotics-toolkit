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
def get_instances(
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
    Get occurrences of the assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting occurrences.
        id_to_name_map: Mapping of instance IDs to their corresponding sanitized names. This can be obtained
            by calling the `get_instances` function.

    Returns:
        A dictionary mapping occurrence paths to their corresponding occurrences.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_occurrences(assembly)
        {
            "part1": Occurrence(...),
            "subassembly1": Occurrence(...),
            "subassembly1-SUB-part1": Occurrence(...),
            "subassembly1-SUB-subassembly2": Occurrence(...),
        }
    """
    occurrence_map = {}

    for occurrence in assembly.rootAssembly.occurrences:
        try:
            if len(occurrence.path) > max_depth:
                continue

            occurrence_path = [id_to_name_map[path] for path in occurrence.path]
            LOGGER.debug(f"Parsing occurrence: {occurrence_path}")
            occurrence_map[SUBASSEMBLY_JOINER.join(occurrence_path)] = occurrence

        except KeyError:
            LOGGER.warning(f"Occurrence path {occurrence.path} not found")

    return occurrence_map


def get_subassemblies(
    assembly: Assembly, client: Client, instance_map: dict[str, Union[PartInstance, AssemblyInstance]]
) -> tuple[dict[str, SubAssembly], dict[str, RootAssembly]]:
    """
    Get subassemblies of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting subassemblies.
        client: The client object to make API calls.
        instance_map: Mapping of instance IDs to their corresponding instances.
                      This can be obtained by calling the `get_instances` function.

    Returns:
        A tuple containing:
        - A dictionary mapping subassembly IDs to their corresponding subassembly objects.
        - A dictionary mapping subassembly IDs to their corresponding rigid subassembly root assemblies.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_subassemblies(assembly, client, instance_map)
        (
            {
                "subassembly1": SubAssembly(...),
                "subassembly2": SubAssembly(...),
            },
            {
                "subassembly1": RootAssembly(...),
            }
        )
    """
    subassembly_map: dict[str, SubAssembly] = {}
    rigid_subassembly_map: dict[str, RootAssembly] = {}

    # Pre-group instances by their UID
    subassembly_instance_map = {
        instance.uid: [] for instance in instance_map.values() if instance.type == InstanceType.ASSEMBLY
    }
    for key, instance in instance_map.items():
        if instance.type == InstanceType.ASSEMBLY:
            subassembly_instance_map[instance.uid].append(key)

    # Process subassemblies in one loop
    for subassembly in assembly.subAssemblies:
        uid = subassembly.uid
        if uid in subassembly_instance_map:
            is_rigid = len(subassembly.features) == 0 or all(
                feature.featureType == AssemblyFeatureType.MATEGROUP for feature in subassembly.features
            )
            for key in subassembly_instance_map[uid]:
                if is_rigid:
                    # Fetch rigid subassemblies in parallel
                    rigid_subassembly_map[key] = client.get_root_assembly(
                        did=subassembly.documentId,
                        wtype=WorkspaceType.M.value,
                        wid=subassembly.documentMicroversion,
                        eid=subassembly.elementId,
                        with_mass_properties=True,
                        log_response=False,
                    )
                else:
                    subassembly_map[key] = subassembly

    return subassembly_map, rigid_subassembly_map


async def _fetch_mass_properties_async(
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


async def _get_parts_async(
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
                tasks.append(_fetch_mass_properties_async(part, key, client, rigid_subassembly_map, part_map))

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
    return asyncio.run(_get_parts_async(assembly, rigid_subassembly_map, client, instance_map))


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


def get_mates_and_relations(  # noqa: C901
    assembly: Assembly,
    subassembly_map: dict[str, SubAssembly],
    rigid_subassembly_map: dict[str, RootAssembly],
    id_to_name_map: dict[str, str],
    parts: dict[str, Part],
) -> tuple[dict[str, MateFeatureData], dict[str, MateRelationFeatureData]]:
    """
    Get mates and relations of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting mates.
        subassembly_map: Mapping of subassembly IDs to their corresponding subassembly objects.
        id_to_name_map: Mapping of instance IDs to their corresponding sanitized names. This can be obtained
            by calling the `get_instances` function.

    Returns:
        A tuple containing:
        - A dictionary mapping mate IDs to their corresponding mate feature data.
        - A dictionary mapping mate relation IDs to their corresponding mate relation feature data.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_mates_and_relations(assembly)
        ({
            "subassembly1-SUB-part1-MATE-subassembly2-SUB-part2": AssemblyFeature(...),
            "part1-MATE-part2": MateFeatureData(...),
        },
        {
            "MuwOg31fsdH/5O2nX": MateRelationFeatureData(...),
        })
    """
    rigid_subassembly_occurrence_map = {}
    for assembly_key, rigid_subassembly in rigid_subassembly_map.items():
        occurrence_map: dict[str, Occurrence] = {}
        for occurrence in rigid_subassembly.occurrences:
            try:
                occurrence_path = [id_to_name_map[path] for path in occurrence.path]
                occurrence_map[SUBASSEMBLY_JOINER.join(occurrence_path)] = occurrence

            except KeyError:
                LOGGER.warning(f"Occurrence path {occurrence.path} not found")

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
        rigid_subassembly_occurrence_map[assembly_key] = occurrence_map

        # parts[assembly_key].rigidAssemblyToPartTF[part_reference] = MatedCS.from_tf(
        #     np.matrix(occurrence_map[part_reference].transform).reshape(4, 4)
        # )

    def traverse_assembly(  # noqa: C901
        root: Union[RootAssembly, SubAssembly], subassembly_prefix: Optional[str] = None
    ) -> tuple[dict[str, MateFeatureData], dict[str, MateRelationFeatureData]]:
        _mates_map: dict[str, MateFeatureData] = {}
        _relations_map: dict[str, MateRelationFeatureData] = {}

        for feature in root.features:
            feature.featureData.id = feature.id

            if feature.suppressed:
                continue

            if feature.featureType == AssemblyFeatureType.MATE:
                if len(feature.featureData.matedEntities) < 2:
                    # TODO: will there be features with just one mated entity?
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

                if parent_occurrences[0] in rigid_subassembly_map:
                    _occurrence: Occurrence = rigid_subassembly_occurrence_map[parent_occurrences[0]].get(
                        parent_occurrences[1]
                    )

                    if _occurrence is not None:
                        parent_parentCS = MatedCS.from_tf(np.matrix(_occurrence.transform).reshape(4, 4))
                        parts[parent_occurrences[0]].rigidAssemblyToPartTF[parent_occurrences[1]] = (
                            parent_parentCS.part_tf
                        )
                        feature.featureData.matedEntities[PARENT].parentCS = parent_parentCS
                    else:
                        LOGGER.warning(f"Occurrence {parent_occurrences[1]} not found within {parent_occurrences[0]}")
                        continue

                    parent_occurrences = [parent_occurrences[0]]

                if child_occurrences[0] in rigid_subassembly_map:
                    _occurrence: Occurrence = rigid_subassembly_occurrence_map[child_occurrences[0]].get(
                        child_occurrences[1]
                    )

                    if _occurrence is not None:
                        child_parentCS = MatedCS.from_tf(np.matrix(_occurrence.transform).reshape(4, 4))
                        parts[child_occurrences[0]].rigidAssemblyToPartTF[child_occurrences[1]] = child_parentCS.part_tf
                        feature.featureData.matedEntities[CHILD].parentCS = child_parentCS
                    else:
                        LOGGER.warning(f"Occurrence {child_occurrences[1]} not found within {child_occurrences[0]}")
                        continue

                    child_occurrences = [child_occurrences[0]]

                _mates_map[
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

                _relations_map[child_joint_id] = feature.featureData

            elif feature.featureType == AssemblyFeatureType.MATECONNECTOR:
                # TODO: Mate connectors' MatedCS data is already included in the MateFeatureData
                pass

            elif feature.featureType == AssemblyFeatureType.MATEGROUP:
                LOGGER.info(f"Assembly has a MATEGROUP feature: {feature}")
                LOGGER.info(
                    "MATEGROUPS are now only supported within subassemblies and are considered as rigid bodies."
                )
                LOGGER.info("For more information, please refer to the documentation.")

        return _mates_map, _relations_map

    mates_map, relations_map = traverse_assembly(assembly.rootAssembly)

    for key, subassembly in subassembly_map.items():
        sub_mates_map, sub_relations_map = traverse_assembly(subassembly, key)
        mates_map.update(sub_mates_map)
        relations_map.update(sub_relations_map)

    return mates_map, relations_map
