# Editing an Onshape Assembly

In this tutorial, you'll learn how to use the `onshape-api` Python library to interact with an Onshape document, modify variables, parse an assembly, and generate a URDF file for use in robotics simulations.

---

## Prerequisites

Before proceeding, ensure you have:

- Installed the `onshape-api` library:
  ```bash
  pip install onshape-api
  ```
- Valid API keys set up in a `.env` file. Refer to the [Getting Started](../getting-started.md) section for details.
- Access to the Onshape document you want to work with. For this tutorial, we’ll use the following example document:
  [Example Onshape Document](https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812).

---

## Step-by-Step Guide

### Step 1: Initialize the Onshape Client

First, set up the client to authenticate and interact with the Onshape API:

```python
import onshape_api as osa

# Initialize the client
client = osa.Client()
```

---

### Step 2: Access the Onshape Document

Use the document URL to create a `Document` object:

```python
doc = osa.Document.from_url(
    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
)
```

---

### Step 3: Modify Variables

Fetch and modify the variables in the document:

```python
# Retrieve document elements and variables
elements = client.get_elements(doc.did, doc.wtype, doc.wid)
variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)

# Update variable values
variables["wheelDiameter"].expression = "300 mm"
variables["wheelThickness"].expression = "71 mm"
variables["forkAngle"].expression = "20 deg"

# Apply the changes
client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
```

---

### Step 4: Retrieve Assembly Data

Get assembly information and parse its components:

```python
from onshape_api.parse import (
    get_instances,
    get_mates_and_relations,
    get_occurences,
    get_parts,
    get_subassemblies,
)

# Get the assembly
assembly, _ = client.get_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id)

# Extract components
instances, id_to_name_map = get_instances(assembly)
occurences = get_occurences(assembly, id_to_name_map)
subassemblies = get_subassemblies(assembly, instances)
parts = get_parts(assembly, client, instances)
mates, relations = get_mates_and_relations(assembly, subassembly_map=subassemblies, id_to_name_map=id_to_name_map)
```

---

### Step 5: Visualize the Assembly Graph

Use the graphing tools to visualize the structure of the assembly:

```python
from onshape_api.graph import create_graph, show_graph

# Create and show the graph
graph, root_node = create_graph(occurences=occurences, instances=instances, parts=parts, mates=mates)
show_graph(graph)
```

---

### Step 6: Generate URDF Components

Convert the parsed assembly into URDF components:

```python
from onshape_api.urdf import get_urdf_components
from onshape_api.models.robot import Robot

# Generate URDF links and joints
links, joints = get_urdf_components(assembly, graph, root_node, parts, mates, relations, client)

# Create a Robot object
robot = Robot(name="bike", links=links, joints=joints)

# Save the URDF file
robot.save("bike.urdf")
```

---

## Result

After running the script, you’ll have a `bike.urdf` file in your working directory. This file represents the robot assembly and can be used in robotics simulators like <a href="https://gazebosim.org/home" target="_blank">Gazebo</a> or <a href="https://developer.nvidia.com/isaac/sim" target="_blank">Isaac Sim</a>

---
