"""
This module contains functions that provide a way to traverse the assembly structure, extract information about parts,
subassemblies, instances, and mates, and generate a hierarchical representation of the assembly.

"""

import os
from typing import Optional, Union

from onshape_api.connect import Client
from onshape_api.log import LOGGER
from onshape_api.models.assembly import (
    Assembly,
    AssemblyFeature,
    AssemblyFeatureType,
    AssemblyInstance,
    InstanceType,
    MateFeatureData,
    Occurrence,
    Part,
    PartInstance,
    RootAssembly,
    SubAssembly,
)
from onshape_api.utilities.helpers import get_sanitized_name

os.environ["TCL_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ["TK_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"

SUBASSEMBLY_JOINER = "-SUB-"
MATE_JOINER = "-MATE-"

CHILD = 0
PARENT = 1


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


def get_occurences(assembly: Assembly, id_to_name_map: dict[str, str]) -> dict[str, Occurrence]:
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
        >>> get_occurences(assembly)
        {
            "part1": Occurrence(...),
            "subassembly1": Occurrence(...),
            "subassembly1-SUB-part1": Occurrence(...),
            "subassembly1-SUB-subassembly2": Occurrence(...),
        }
    """
    occurence_map = {}

    for occurence in assembly.rootAssembly.occurrences:
        try:
            occurence_path = [id_to_name_map[path] for path in occurence.path]
            occurence_map[SUBASSEMBLY_JOINER.join(occurence_path)] = occurence

        except KeyError:
            LOGGER.warning(f"Occurrence path {occurence.path} not found")

    return occurence_map


def get_subassemblies(
    assembly: Assembly, instance_map: dict[str, Union[PartInstance, AssemblyInstance]]
) -> dict[str, SubAssembly]:
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
    subassembly_map = {}

    subassembly_instance_map = {
        instance.uid: key for key, instance in instance_map.items() if instance.type == InstanceType.ASSEMBLY
    }
    for subassembly in assembly.subAssemblies:
        if subassembly.uid in subassembly_instance_map:
            subassembly_map[subassembly_instance_map[subassembly.uid]] = subassembly

    return subassembly_map


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
        if part.uid in part_instance_map:
            for key in part_instance_map[part.uid]:
                part.MassProperty = client.get_mass_property(
                    part.documentId, assembly.document.wid, part.elementId, part.partId
                )
                part_map[key] = part

    return part_map


def join_mate_occurences(parent: list[str], child: list[str], prefix: Optional[str] = None) -> str:
    """
    Join two occurrence paths with a mate joiner.

    Args:
        parent: Occurrence path of the parent entity.
        child: Occurrence path of the child entity.
        prefix: Prefix to add to the occurrence path.

    Returns:
        The joined occurrence path.

    Examples:
        >>> join_mate_occurences(["subassembly1", "part1"], ["subassembly2"])
        "subassembly1-SUB-part1-MATE-subassembly2"

        >>> join_mate_occurences(["part1"], ["part2"])
        "part1-MATE-part2"
    """
    parent_occurence = SUBASSEMBLY_JOINER.join(parent)
    child_occurence = SUBASSEMBLY_JOINER.join(child)

    if prefix is not None:
        return (
            f"{prefix}{SUBASSEMBLY_JOINER}{parent_occurence}{MATE_JOINER}"
            f"{prefix}{SUBASSEMBLY_JOINER}{child_occurence}"
        )
    else:
        return f"{parent_occurence}{MATE_JOINER}{child_occurence}"


def get_mates(
    assembly: Assembly,
    subassembly_map: dict[str, SubAssembly],
    id_to_name_map: dict[str, str],
) -> dict[str, AssemblyFeature]:
    """
    Get mates of the assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting mates.
        subassembly_map: Mapping of subassembly IDs to their corresponding subassembly objects.

    Returns:
        A dictionary mapping occurrence paths to their corresponding mate data.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_mates(assembly)
        {
            "subassembly1-SUB-part1-MATE-subassembly2-SUB-part2": AssemblyFeature(...),
            "part1-MATE-part2": AssemblyFeature(...),
        }
    """

    def traverse_assembly(
        root: Union[RootAssembly, SubAssembly], subassembly_prefix: Optional[str] = None
    ) -> dict[str, MateFeatureData]:
        _mates_map = {}

        for feature in root.features:
            if feature.featureType == AssemblyFeatureType.MATE and not feature.suppressed:
                if len(feature.featureData.matedEntities) < 2:
                    # TODO: will there be features with just one mated entity?
                    LOGGER.warning(f"Invalid mate feature: {feature}")
                    continue

                child_occurences = [
                    id_to_name_map[path] for path in feature.featureData.matedEntities[CHILD].matedOccurrence
                ]
                parent_occurences = [
                    id_to_name_map[path] for path in feature.featureData.matedEntities[PARENT].matedOccurrence
                ]

                feature.featureData.matedEntities[CHILD].matedOccurrence = child_occurences
                feature.featureData.matedEntities[PARENT].matedOccurrence = parent_occurences

                _mates_map[
                    join_mate_occurences(
                        parent=parent_occurences,
                        child=child_occurences,
                        prefix=subassembly_prefix,
                    )
                ] = feature.featureData

        return _mates_map

    mates_map = traverse_assembly(assembly.rootAssembly)

    for key, subassembly in subassembly_map.items():
        mates_map.update(traverse_assembly(subassembly, key))

    return mates_map
