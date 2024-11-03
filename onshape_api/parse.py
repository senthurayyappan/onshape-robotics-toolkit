import os
from typing import Optional, Union

from onshape_api.connect import Client
from onshape_api.models.assembly import (
    Assembly,
    AssemblyFeatureType,
    Instance,
    InstanceType,
    MateFeature,
    MateFeatureData,
    Occurrence,
    Part,
    RootAssembly,
    SubAssembly,
)
from onshape_api.models.mass import MassModel

os.environ["TCL_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ["TK_LIBRARY"] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"

SUBASSEMBLY_JOINER = "<::>"
MATE_JOINER = "<+>"


def get_instances(assembly: Assembly) -> dict[str, Instance]:
    """
    Get instances of an occurrence path in the assembly.

    Args:
        assembly: The assembly object.

    Returns:
        A dictionary mapping instance IDs to their corresponding instances.
    """

    def traverse_instances(root: Union[RootAssembly, SubAssembly], prefix: str = "") -> dict[str, Instance]:
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
    occurence_mapping = {}
    for occurence in assembly.rootAssembly.occurrences:
        occurence_mapping[SUBASSEMBLY_JOINER.join(occurence.path)] = occurence

    return occurence_mapping


def get_subassemblies(
    assembly: Assembly, instance_mapping: Optional[dict[str, Instance]] = None
) -> dict[str, SubAssembly]:
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


def get_parts(assembly: Assembly, instance_mapping: Optional[dict[str, Instance]] = None) -> dict[str, Part]:
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
                part_mapping[key] = part

    return part_mapping


def get_mass_properties(parts: dict[str, Part], workspaceId: str, client: Client) -> dict[str, MassModel]:
    _mass_properties = {}
    for part in parts:
        _mass_properties[part] = client.get_mass_properties(
            parts[part].documentId, workspaceId, parts[part].elementId, parts[part].partId
        )
    return _mass_properties


def join_mate_occurences(child: list[str], parent: list[str], prefix: Optional[str] = None) -> str:
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
) -> dict[str, MateFeature]:
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
