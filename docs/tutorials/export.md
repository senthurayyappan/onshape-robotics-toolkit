# Exporting an Onshape Assembly to URDF

This tutorial demonstrates a streamlined workflow for converting an Onshape assembly to a URDF file using the `onshape-api` library. Follow these steps to easily generate a URDF file and visualize your assembly's structure.

<img src="export-header.gif" alt="Export Header" style="width: 100%;">

---

## Prerequisites

Before you begin, ensure the following:

- **Install the library**: You have the `onshape-api` library installed.
  ```bash
  pip install onshape-api
  ```
- **API Keys**: Set up your Onshape API keys in a `.env` file. Refer to the [Getting Started](../getting-started.md) guide if needed.
- **Document URL**: Have the URL of the Onshape assembly you want to convert. For this example, we’ll use:
  <a href="https://cad.onshape.com/documents/00fdecd70b9459267a70825e/w/5b8859e00b5d129724548da1/e/8bb8553f756c40770e11d5b4" target="_blank">Arbor Press Assembly</a>.

---

## Workflow: Onshape Assembly to URDF

### Step 1: Initialize the Client

Start by setting up the Onshape API client to authenticate and interact with your Onshape account:

```python
import os
import onshape_api as osa
from onshape_api.models.document import Document

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

client = osa.Client(
    env="./.env"
)
```

---

### Step 2: Load the Onshape Assembly

Use the assembly’s URL to load the document and fetch its details:

```python
# Replace with your Onshape assembly URL
document = Document.from_url(
    "https://cad.onshape.com/documents/00fdecd70b9459267a70825e/w/5b8859e00b5d129724548da1/e/8bb8553f756c40770e11d5b4"
)

assembly = client.get_assembly(
    did=document.did,
    wtype=document.wtype,
    wid=document.wid,
    eid=document.eid,
    with_meta_data=True,
)
```

---

### Step 3: Parse the Assembly Components

Extract instances, occurrences, parts, subassemblies, and relational data:

```python
instances, id_to_name_map = osa.get_instances(assembly)
occurrences = osa.get_occurrences(assembly, id_to_name_map)
parts = osa.get_parts(assembly, client, instances)
subassemblies = osa.get_subassemblies(assembly, instances)
mates, relations = osa.get_mates_and_relations(assembly, subassemblies, id_to_name_map)
```

---

### Step 4: Visualize the Assembly Graph

Create and save a graph representation of the assembly’s structure:

```python
graph, root_node = osa.create_graph(
    occurrences=occurrences,
    instances=instances,
    parts=parts,
    mates=mates,
)
osa.plot_graph(graph, f"{assembly.document.name + '-' + assembly.name}.png")
```

This will save a PNG file of the assembly graph in your current working directory.

<img src="assembly-graph.png" alt="Assembly Graph" style="width: 100%;">

---

### Step 5: Generate the URDF File

Convert the parsed assembly data into a URDF file:

```python
robot = osa.get_robot(
    assembly=assembly,
    graph=graph,
    root_node=root_node,
    parts=parts,
    mates=mates,
    relations=relations,
    client=client,
    robot_name=f"{assembly.document.name + '-' + assembly.name}",
)

robot.save(f"{assembly.document.name + '-' + assembly.name}.urdf")
```

<img src="assembly-urdf.gif" alt="Assembly Graph" style="width: 100%;">

---

## Result

After running the script, you’ll find two files in your working directory:

1. A visual representation of the assembly graph (e.g., `document-name-assembly-name.png`).
2. The URDF file (e.g., `document-name-assembly-name.urdf`).

The URDF file can now be used in robotics simulators such as Gazebo or integrated with ROS.
