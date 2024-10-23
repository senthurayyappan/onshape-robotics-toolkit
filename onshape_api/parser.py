import os
from typing import Optional, Union

from onshape_api.models.assembly import Assembly, Instance, InstanceType, RootAssembly, SubAssembly, Occurrence

os.environ['TCL_LIBRARY'] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tcl8.6"
os.environ['TK_LIBRARY'] = "C:\\Users\\imsen\\AppData\\Local\\Programs\\Python\\Python313\\tcl\\tk8.6"

PREFIX_JOINER = ">"

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
            instance_id = f"{prefix}{PREFIX_JOINER}{instance.id}" if prefix else instance.id
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
        occurence_mapping[PREFIX_JOINER.join(occurence.path)] = occurence

    return occurence_mapping
