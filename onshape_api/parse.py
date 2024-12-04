"""
This module contains functions that provide a way to traverse the assembly structure, extract information about parts,
subassemblies, instances, and mates, and generate a hierarchical representation of the assembly.

"""

import copy
import os
from typing import Optional, Union

from onshape_api.connect import Client
from onshape_api.log import LOGGER
from onshape_api.models.assembly import (
    Assembly,
    AssemblyFeatureType,
    AssemblyInstance,
    InstanceType,
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
from onshape_api.utilities.helpers import get_sanitized_name, save_model_as_json

os.environ["TCL_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ["TK_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"

SUBASSEMBLY_JOINER = "-SUB-"
MATE_JOINER = "_to_"

CHILD = 0
PARENT = 1

RELATION_CHILD = 1
RELATION_PARENT = 0


# TODO: get_mate_connectors method to parse part mate connectors that maybe useful to someone
def get_instances(assembly: Assembly) -> tuple[dict[str, Union[PartInstance, AssemblyInstance]], dict[str, str]]:
    """
    Get instances and their sanitized names from an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting instances.

    Returns:
        A tuple containing:
        - A dictionary mapping instance IDs to their corresponding instances.
        - A dictionary mapping instance IDs to their sanitized names.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_instances(assembly)
        (
            {
                "part1": PartInstance(...),
                "subassembly1": AssemblyInstance(...),
                "subassembly1-SUB-part1": PartInstance(...),
                "subassembly1-SUB-subassembly2": AssemblyInstance(...),
            },
            {
                "part1": "part1",
                "subassembly1": "subassembly1",
                "subassembly1-SUB-part1": "part1",
                "subassembly1-SUB-subassembly2": "subassembly2",
            }
        )
    """

    def traverse_instances(
        root: Union[RootAssembly, SubAssembly], prefix: str = ""
    ) -> tuple[dict[str, Union[PartInstance, AssemblyInstance]], dict[str, str]]:
        """
        Traverse the assembly structure to get instances.

        Args:
            root: Root assembly or subassembly object to traverse.
            prefix: Prefix for the instance ID.

        Returns:
            A tuple containing:
            - A dictionary mapping instance IDs to their corresponding instances.
            - A dictionary mapping instance IDs to their sanitized names.

        Examples:
            >>> root = RootAssembly(...)
            >>> traverse_instances(root)
            (
                {
                    "part1": PartInstance(...),
                    "subassembly1": AssemblyInstance(...),
                    "subassembly1-SUB-part1": PartInstance(...),
                    "subassembly1-SUB-subassembly2": AssemblyInstance(...),
                },
                {
                    "part1": "part1",
                    "subassembly1": "subassembly1",
                    "subassembly1-SUB-part1": "part1",
                    "subassembly1-SUB-subassembly2": "subassembly2",
                }
            )
        """
        instance_map = {}
        id_to_name_map = {}

        for instance in root.instances:
            sanitized_name = get_sanitized_name(instance.name)
            LOGGER.info(f"Parsing instance: {sanitized_name}")
            instance_id = f"{prefix}{SUBASSEMBLY_JOINER}{sanitized_name}" if prefix else sanitized_name
            id_to_name_map[instance.id] = sanitized_name
            instance_map[instance_id] = instance

            if instance.type == InstanceType.ASSEMBLY:
                for sub_assembly in assembly.subAssemblies:
                    if sub_assembly.uid == instance.uid:
                        sub_instance_map, sub_id_to_name_map = traverse_instances(sub_assembly, instance_id)
                        instance_map.update(sub_instance_map)
                        id_to_name_map.update(sub_id_to_name_map)

        return instance_map, id_to_name_map

    return traverse_instances(assembly.rootAssembly)


def get_occurrences(assembly: Assembly, id_to_name_map: dict[str, str]) -> dict[str, Occurrence]:
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
            occurrence_path = [id_to_name_map[path] for path in occurrence.path]
            LOGGER.info(f"Parsing occurrence: {occurrence_path}")
            occurrence_map[SUBASSEMBLY_JOINER.join(occurrence_path)] = occurrence

        except KeyError:
            LOGGER.warning(f"Occurrence path {occurrence.path} not found")

    return occurrence_map


def get_subassemblies(
    assembly: Assembly, client: Client, instance_map: dict[str, Union[PartInstance, AssemblyInstance]]
) -> tuple[dict[str, SubAssembly], dict[str, SubAssembly]]:
    """
    Get subassemblies of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting subassemblies.
        instance_map: Mapping of instance IDs to their corresponding instances. This can be obtained
            by calling the `get_instances` function.

    Returns:
        A dictionary mapping subassembly IDs to their corresponding subassembly objects.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_subassemblies(assembly)
        {
            "subassembly1": SubAssembly(...),
            "subassembly2": SubAssembly(...),
        }
    """
    subassembly_map: dict[str, SubAssembly] = {}
    rigid_subassembly_map: dict[str, RootAssembly] = {}

    subassembly_instance_map: dict[str, list[str]] = {}

    for key, instance in instance_map.items():
        if instance.type == InstanceType.ASSEMBLY:
            subassembly_instance_map.setdefault(instance.uid, []).append(key)

    for subassembly in assembly.subAssemblies:
        LOGGER.info(f"Parsing subassembly: {subassembly.uid}")
        if subassembly.uid in subassembly_instance_map:
            for key in subassembly_instance_map[subassembly.uid]:
                if len(subassembly.features) == 0 or all(
                    feature.featureType == AssemblyFeatureType.MATEGROUP for feature in subassembly.features
                ):
                    rigid_subassembly_map[key] = client.get_root_assembly(
                        did=subassembly.documentId,
                        wtype=WorkspaceType.W.value,
                        wid=assembly.document.wid,
                        eid=subassembly.elementId,
                        with_mass_properties=True,
                        log_response=True,
                    )
                    save_model_as_json(rigid_subassembly_map[key], f"{key}.json")

                    print(rigid_subassembly_map[key].occurrences)

                else:
                    subassembly_map[key] = subassembly

    return subassembly_map, rigid_subassembly_map


def get_parts(
    assembly: Assembly,
    client: Client,
    instance_map: dict[str, Union[PartInstance, AssemblyInstance]],
) -> dict[str, Part]:
    """
    Get parts of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting parts.
        client: The Onshape client object to use for sending API requests.
        instance_map: Mapping of instance IDs to their corresponding instances. This can be obtained
            by calling the `get_instances` function.

    Returns:
        A dictionary mapping part IDs to their corresponding part objects.

    Examples:
        >>> assembly = Assembly(...)
        >>> client = Client(...)
        >>> get_parts(assembly, client)
        {
            "part1": Part(...),
            "part2": Part(...),
        }
    """

    # NOTE: partIDs are not unique hence we use the instance ID as the key
    part_instance_map: dict[str, list[str]] = {}
    part_map: dict[str, Part] = {}

    for key, instance in instance_map.items():
        if instance.type == InstanceType.PART:
            part_instance_map.setdefault(instance.uid, []).append(key)

    for part in assembly.parts:
        LOGGER.info(f"Parsing part: {part.partId}")
        if part.uid in part_instance_map:
            for key in part_instance_map[part.uid]:
                part.MassProperty = client.get_mass_property(
                    did=part.documentId,
                    wid=assembly.document.wid,
                    eid=part.elementId,
                    partID=part.partId,
                    vid=part.documentVersion,
                )
                part_map[key] = part

    return part_map


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
    rigid_subassembly_map: dict[str, SubAssembly],
    id_to_name_map: dict[str, str],
    occurences_map: dict[str, Occurrence],
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
    for key, rigid_subassembly in rigid_subassembly_map.items():
        rigid_subassembly_parts = [part_name for part_name in parts if part_name.startswith(key)]
        for part_key in rigid_subassembly_parts:
            parts[part_key] = copy.deepcopy(parts[part_key])
            parts[part_key].isRigidAssembly = True
            parts[part_key].documentId = rigid_subassembly.documentId
            parts[part_key].elementId = rigid_subassembly.elementId
            parts[part_key].documentMicroversion = rigid_subassembly.documentMicroversion
            parts[part_key].documentVersion = None
            parts[part_key].MassProperty = rigid_subassembly.MassProperty

    def traverse_assembly(
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
