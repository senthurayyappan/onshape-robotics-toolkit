# Sequence Diagram

<body>
    <pre class="mermaid">
    sequenceDiagram
        participant User as User
        participant Client as onshape-robotics-toolkit.client
        participant Onshape as Onshape Server
        participant Robot as onshape-robotics-toolkit.robot

        User->>Client: Initialize Client with API Keys
        Client->>Onshape: Authenticate with Access Key & Secret Key
        Onshape-->>Client: Return Authentication Token

        User->>Client: Request Document Information (e.g., document URL)
        Client->>Onshape: Send GET request for Document Details
        Onshape-->>Client: Return Document Metadata (JSON)
        Client-->>User: Deliver Document Metadata

        User->>Client: Request CAD Assembly
        Client->>Onshape: Send GET request for Assembly Details
        Onshape-->>Client: Return Assembly Data (JSON)
        Client-->>User: Deliver Assembly Data

        User->>Robot: Initiate URDF Export Workflow
        Robot-->>Onshape: Parse Assembly Data for URDF
        Robot-->>User: Deliver Robot model (URDF)

        User->>User: Use URDF for Simulation or Control

</body>
