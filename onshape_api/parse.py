"""
This module contains functions that provide a way to traverse the assembly structure, extract information about parts,
subassemblies, instances, and mates, and generate a hierarchical representation of the assembly.

"""

import os
from typing import Optional, Union

from onshape_api.connect import Client
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

os.environ["TCL_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ["TK_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"

SUBASSEMBLY_JOINER = "<::>"
MATE_JOINER = "<+>"


def get_instances(assembly: Assembly) -> dict[str, Union[PartInstance, AssemblyInstance]]:
    """
    Get instances of an occurrence path in the assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting instances.

    Returns:
        A dictionary mapping instance IDs to their corresponding instances.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_instances(assembly)
        {
            "part1": PartInstance(...),
            "subassembly1": AssemblyInstance(...),
            "subassembly1<::>part1": PartInstance(...),
            "subassembly1<::>subassembly2": AssemblyInstance(...),
        }
    """

    def traverse_instances(
        root: Union[RootAssembly, SubAssembly], prefix: str = ""
    ) -> dict[str, Union[PartInstance, AssemblyInstance]]:
        """
        Traverse the assembly structure to get instances.

        Args:
            root: Root assembly or subassembly object to traverse.
            prefix: Prefix for the instance ID.

        Returns:
            A dictionary mapping instance IDs to their corresponding instances.

        Examples:
            >>> root = RootAssembly(...)
            >>> traverse_instances(root)
            {
                "part1": PartInstance(...),
                "subassembly1": AssemblyInstance(...),
                "subassembly1<::>part1": PartInstance(...),
                "subassembly1<::>subassembly2": AssemblyInstance(...),
            }
        """
        instance_mapping = {}
        for instance in root.instances:
            instance_id = f"{prefix}{SUBASSEMBLY_JOINER}{instance.id}" if prefix else instance.id
            instance_mapping[instance_id] = instance

            if instance.type == InstanceType.ASSEMBLY:
                for sub_assembly in assembly.subAssemblies:
                    if sub_assembly.uid == instance.uid:
                        instance_mapping.update(traverse_instances(sub_assembly, instance_id))
        return instance_mapping

    return traverse_instances(assembly.rootAssembly)


def get_occurences(assembly: Assembly) -> dict[str, Occurrence]:
    """
    Get occurrences of the assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting occurrences.

    Returns:
        A dictionary mapping occurrence paths to their corresponding occurrences.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_occurences(assembly)
        {
            "part1": Occurrence(...),
            "subassembly1": Occurrence(...),
            "subassembly1<::>part1": Occurrence(...),
            "subassembly1<::>subassembly2": Occurrence(...),
        }
    """
    occurence_mapping = {}
    for occurence in assembly.rootAssembly.occurrences:
        occurence_mapping[SUBASSEMBLY_JOINER.join(occurence.path)] = occurence

    return occurence_mapping


def get_subassemblies(
    assembly: Assembly, instance_mapping: Optional[dict[str, Union[PartInstance, AssemblyInstance]]] = None
) -> dict[str, SubAssembly]:
    """
    Get subassemblies of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting subassemblies.
        instance_mapping: Mapping of instance IDs to their corresponding instances.

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
    subassembly_mapping = {}

    if instance_mapping is None:
        instance_mapping = get_instances(assembly)

    subassembly_instance_mapping = {
        instance.uid: key for key, instance in instance_mapping.items() if instance.type == InstanceType.ASSEMBLY
    }
    for subassembly in assembly.subAssemblies:
        if subassembly.uid in subassembly_instance_mapping:
            subassembly_mapping[subassembly_instance_mapping[subassembly.uid]] = subassembly

    return subassembly_mapping


def get_parts(
    assembly: Assembly,
    client: Client,
    instance_mapping: Optional[dict[str, Union[PartInstance, AssemblyInstance]]] = None,
) -> dict[str, Part]:
    """
    Get parts of an Onshape assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting parts.
        client: The Onshape client object to use for sending API requests.
        instance_mapping: Mapping of instance IDs to their corresponding instances.

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
    part_instance_mapping: dict[str, list[str]] = {}
    part_mapping: dict[str, Part] = {}

    if instance_mapping is None:
        instance_mapping = get_instances(assembly)

    for key, instance in instance_mapping.items():
        if instance.type == InstanceType.PART:
            part_instance_mapping.setdefault(instance.uid, []).append(key)

    for part in assembly.parts:
        if part.uid in part_instance_mapping:
            for key in part_instance_mapping[part.uid]:
                part.MassProperty = client.get_mass_property(
                    part.documentId, assembly.document.wid, part.elementId, part.partId
                )
                part_mapping[key] = part

    return part_mapping


def join_mate_occurences(child: list[str], parent: list[str], prefix: Optional[str] = None) -> str:
    """
    Join two occurrence paths with a mate joiner.

    Args:
        child: Occurrence path of the child entity.
        parent: Occurrence path of the parent entity.
        prefix: Prefix to add to the occurrence path.

    Returns:
        The joined occurrence path.

    Examples:
        >>> join_mate_occurences(["subassembly1", "part1"], ["subassembly2"])
        "subassembly1<::>part1<+>subassembly2"

        >>> join_mate_occurences(["part1"], ["part2"])
        "part1<+>part2"
    """
    child_occurence = SUBASSEMBLY_JOINER.join(child)
    parent_occurence = SUBASSEMBLY_JOINER.join(parent)

    if prefix is not None:
        return (
            f"{prefix}{SUBASSEMBLY_JOINER}{child_occurence}{MATE_JOINER}"
            f"{prefix}{SUBASSEMBLY_JOINER}{parent_occurence}"
        )
    else:
        return f"{child_occurence}{MATE_JOINER}{parent_occurence}"


def get_mates(
    assembly: Assembly,
    subassembly_mapping: Optional[dict[str, SubAssembly]] = None,
) -> dict[str, AssemblyFeature]:
    """
    Get mates of the assembly.

    Args:
        assembly: The Onshape assembly object to use for extracting mates.
        subassembly_mapping: Mapping of subassembly IDs to their corresponding subassembly objects.

    Returns:
        A dictionary mapping occurrence paths to their corresponding mate data.

    Examples:
        >>> assembly = Assembly(...)
        >>> get_mates(assembly)
        {
            "subassembly1<::>part1<+>subassembly2<::>part2": AssemblyFeature(...),
            "part1<+>part2": AssemblyFeature(...),
        }
    """

    def traverse_assembly(
        root: Union[RootAssembly, SubAssembly], subassembly_prefix: Optional[str] = None
    ) -> dict[str, MateFeatureData]:
        _mates_mapping = {}

        for feature in root.features:
            if feature.featureType == AssemblyFeatureType.MATE and not feature.suppressed:
                _mates_mapping[
                    join_mate_occurences(
                        child=feature.featureData.matedEntities[0].matedOccurrence,
                        parent=(
                            feature.featureData.matedEntities[1].matedOccurrence
                            if len(feature.featureData.matedEntities) > 1
                            else []
                        ),
                        prefix=subassembly_prefix,
                    )
                ] = feature.featureData

        return _mates_mapping

    mates_mapping = traverse_assembly(assembly.rootAssembly)

    if subassembly_mapping is None:
        subassembly_mapping = get_subassemblies(assembly)

    for key, subassembly in subassembly_mapping.items():
        mates_mapping.update(traverse_assembly(subassembly, key))

    return mates_mapping
