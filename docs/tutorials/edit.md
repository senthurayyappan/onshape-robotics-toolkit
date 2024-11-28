In this tutorial, we’ll explore how to edit an Onshape CAD assembly by modifying its variables in the Variable Studio and exporting the resulting assembly to a URDF file using the `onshape-api` Python library.

<img src="bike-header.gif" alt="Bike Header" style="width: 100%;">

---

## Prerequisites

Before you begin, make sure you have:

- **Installed the `onshape-api` library**:
  ```bash
  pip install onshape-api
  ```
- **API Keys**: Set up your Onshape API keys in a `.env` file as outlined in the [Getting Started](../getting-started.md) guide.
- **Access to the Onshape Document**: Use a CAD document with a Variable Studio. For this tutorial, we’ll use the following example:
  <a href="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812" target="_blank">Example CAD Document</a>.

---

## Step-by-Step Workflow

### Step 1: Initialize the Onshape Client

Set up the Onshape API client for authentication and interaction:

```python
import onshape_api as osa

# Initialize the client
client = osa.Client(
    env="./.env"
)
```

---

### Step 2: Access the CAD Document and Variables

Use the CAD document URL to create a `Document` object and fetch its variables:

```python
doc = osa.Document.from_url(
    url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
)

# Retrieve the Variable Studio element
elements = client.get_elements(doc.did, doc.wtype, doc.wid)
variables = client.get_variables(doc.did, doc.wid, elements["variables"].id)
```

---

### Step 3: Modify Variables in the Variable Studio

Edit the variables to adjust the CAD assembly dimensions. For example, modify the wheel diameter, wheel thickness, and fork angle:

```python
variables["wheelDiameter"].expression = "300 mm"
variables["wheelThickness"].expression = "71 mm"
variables["forkAngle"].expression = "20 deg"

# Save the updated variables back to the Variable Studio
client.set_variables(doc.did, doc.wid, elements["variables"].id, variables)
```

---

### Step 4: Retrieve and Parse the Assembly

Fetch the assembly data and parse its components:

```python
from onshape_api.parse import (
    get_instances,
    get_mates_and_relations,
    get_occurrences,
    get_parts,
    get_subassemblies,
)

# Retrieve the assembly
assembly, _ = client.get_assembly(doc.did, doc.wtype, doc.wid, elements["assembly"].id)

# Extract components
instances, id_to_name_map = get_instances(assembly)
occurrences = get_occurrences(assembly, id_to_name_map)
subassemblies = get_subassemblies(assembly, instances)
parts = get_parts(assembly, client, instances)
mates, relations = get_mates_and_relations(assembly, subassembly_map=subassemblies, id_to_name_map=id_to_name_map)
```

---

### Step 5: Visualize the Assembly Graph

Generate a graph visualization of the assembly structure:

```python
from onshape_api.graph import create_graph, plot_graph

# Create and save the assembly graph
graph, root_node = create_graph(occurrences=occurrences, instances=instances, parts=parts, mates=mates)
plot_graph(graph, "bike.png")
```

<img src="bike-graph.png" alt="Bike Graph" style="width: 100%;">

This will save an image of the assembly graph (`bike.png`) in your current working directory.

---

### Step 6: Export the Assembly to a URDF File

Convert the assembly into a URDF file for robotics applications:

```python
from onshape_api.urdf import get_urdf_components
from onshape_api.models.robot import Robot

# Generate URDF links and joints
links, joints = get_urdf_components(assembly, graph, root_node, parts, mates, relations, client)

# Create and save the URDF file
robot = Robot(name="bike", links=links, joints=joints)
robot.save("bike.urdf")
```

<img src="bike-urdf.gif" alt="Bike URDF" style="width: 100%;">

---

## Result

After completing the steps, you will have:

1. A visualization of the updated assembly graph saved as `bike.png`.
2. A URDF file (`bike.urdf`) representing the edited assembly.

The URDF file can now be used in robotics simulators like Gazebo or integrated into ROS-based projects.
