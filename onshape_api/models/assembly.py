"""
This module contains the data models for the Assembly API responses from Onshape REST API. The data models are Pydantic
BaseModel classes that are used to parse the JSON responses from the API into Python objects. The data models are used
to validate the JSON responses and to provide type hints for the data structures.

Models:
- Occurrence: Occurence model
- Part: Part data model
- PartInstance: Part Instance model
- AssemblyInstance: Assembly Instance model
- AssemblyFeature: AssemblyFeature data model
- Pattern: Pattern data model
- SubAssembly: SubAssembly data model
- RootAssembly: RootAssembly data model
- Assembly: Assembly data model

Supplementary models:
- IDBase: Base model for Part, SubAssembly, and AssemblyInstance in Assembly context
- MatedCS: Mated CS model
- MatedEntity: MatedEntity data model
- MateRelationMate: MateRelationMate data model
- MateGroupFeatureOccurrence: MateGroupFeatureOccurrence data model
- MateGroupFeatureData: MateGroupFeatureData data model
- MateConnectorFeatureData: MateConnectorFeatureData data model
- MateRelationFeatureData: MateRelationFeatureData data model
- MateFeatureData: MateFeatureData data model

Enums:
- INSTANCE_TYPE: Instance type to distinguish between Part and Assembly
- MATE_TYPE: Type of mate between two parts or assemblies, e.g. SLIDER, CYLINDRICAL, REVOLUTE, etc.
- RELATION_TYPE: Type of mate relation between two parts or assemblies, e.g. LINEAR, GEAR, SCREW, etc.
- ASSEMBLY_FEATURE_TYPE: Type of assembly feature, e.g. mate, mateRelation, mateGroup, mateConnector

"""

from enum import Enum
from typing import Union

import numpy as np
from pydantic import BaseModel, Field, field_validator

from onshape_api.models.document import Document
from onshape_api.models.mass import MassProperties
from onshape_api.utilities.helpers import generate_uid


class INSTANCE_TYPE(str, Enum):
    """
    Enum to distinguish between Part and Assembly.

    Attributes:
        PART (str): Represents a part instance.
        ASSEMBLY (str): Represents an assembly instance.
    """

    PART = "Part"
    ASSEMBLY = "Assembly"


class MATE_TYPE(str, Enum):
    """
    Enum to represent the type of mate between two parts or assemblies.

    Attributes:
        SLIDER (str): Represents a slider mate.
        CYLINDRICAL (str): Represents a cylindrical mate.
        REVOLUTE (str): Represents a revolute mate.
        PIN_SLOT (str): Represents a pin-slot mate.
        PLANAR (str): Represents a planar mate.
        BALL (str): Represents a ball mate.
        FASTENED (str): Represents a fastened mate.
        PARALLEL (str): Represents a parallel mate.
    """

    SLIDER = "SLIDER"
    CYLINDRICAL = "CYLINDRICAL"
    REVOLUTE = "REVOLUTE"
    PIN_SLOT = "PIN_SLOT"
    PLANAR = "PLANAR"
    BALL = "BALL"
    FASTENED = "FASTENED"
    PARALLEL = "PARALLEL"


class RELATION_TYPE(str, Enum):
    """
    Enum to represent the type of mate relation between two parts or assemblies.

    Attributes:
        LINEAR (str): Represents a linear relation.
        GEAR (str): Represents a gear relation.
        SCREW (str): Represents a screw relation.
        RACK_AND_PINION (str): Represents a rack and pinion relation.
    """

    LINEAR = "LINEAR"
    GEAR = "GEAR"
    SCREW = "SCREW"
    RACK_AND_PINION = "RACK_AND_PINION"


class ASSEMBLY_FEATURE_TYPE(str, Enum):
    """
    Enum to represent the type of assembly feature.

    Attributes:
        MATE (str): Represents a mate feature.
        MATERELATION (str): Represents a mate relation feature.
        MATEGROUP (str): Represents a mate group feature.
        MATECONNECTOR (str): Represents a mate connector feature.
    """

    MATE = "mate"
    MATERELATION = "mateRelation"
    MATEGROUP = "mateGroup"
    MATECONNECTOR = "mateConnector"


class Occurrence(BaseModel):
    """
    Occurrence model representing the state of an instance in an assembly.

    Example JSON representation:
    {
        "fixed": false,
        "transform": [
            0.8660254037844396, 0.0, 0.5000000000000004, 0.09583333333333346,
            0.0, 1.0, 0.0, -1.53080849893419E-19,
            -0.5000000000000004, 0.0, 0.8660254037844396, 0.16598820239201767,
            0.0, 0.0, 0.0, 1.0
        ],
        "hidden": false,
        "path": ["M0Cyvy+yIq8Rd7En0"]
    }

    Attributes:
        fixed (bool): Indicates if the occurrence is fixed in space.
        transform (list[float]): A 4x4 transformation matrix represented as a list of 16 floats.
        hidden (bool): Indicates if the occurrence is hidden.
        path (list[str]): A list of strings representing the path to the instance.
    """

    fixed: bool = Field(..., description="Indicates if the occurrence is fixed in space.")
    transform: list[float] = Field(..., description="A 4x4 transformation matrix represented as a list of 16 floats.")
    hidden: bool = Field(..., description="Indicates if the occurrence is hidden.")
    path: list[str] = Field(..., description="A list of strings representing the path to the instance.")

    @field_validator("transform")
    def check_transform(cls, v: list[float]) -> list[float]:
        """
        Validates that the transform list has exactly 16 values.

        Args:
            v (list[float]): The transform list to validate.

        Returns:
            list[float]: The validated transform list.

        Raises:
            ValueError: If the transform list does not contain exactly 16 values.
        """
        if len(v) != 16:
            raise ValueError("Transform must have 16 values")

        return v


class IDBase(BaseModel):
    """
    Base model for Part, SubAssembly, and AssemblyInstance in Assembly context.

    Example JSON representation:
    {
        "fullConfiguration" : "default",
        "configuration" : "default",
        "documentId" : "a1c1addf75444f54b504f25c",
        "elementId" : "0b0c209535554345432581fe",
        "documentMicroversion" : "12fabf866bef5a9114d8c4d2"
    }

    Attributes:
        fullConfiguration (str): The full configuration of the entity.
        configuration (str): The configuration of the entity.
        documentId (str): The document ID of the entity.
        elementId (str): The element ID of the entity.
        documentMicroversion (str): The microversion of the document.
    """

    fullConfiguration: str = Field(..., description="The full configuration of the entity.")
    configuration: str = Field(..., description="The configuration of the entity.")
    documentId: str = Field(..., description="The document ID of the entity.")
    elementId: str = Field(..., description="The element ID of the entity.")
    documentMicroversion: str = Field(..., description="The microversion of the document.")

    @field_validator("documentId", "elementId", "documentMicroversion")
    def check_ids(cls, v: str) -> str:
        """
        Validates that the ID fields have exactly 24 characters.

        Args:
            v (str): The ID field to validate.

        Returns:
            str: The validated ID field.

        Raises:
            ValueError: If the ID field does not contain exactly 24 characters.
        """
        if len(v) != 24:
            raise ValueError("DocumentId must have 24 characters")

        return v

    @property
    def uid(self) -> str:
        """
        Generates a unique identifier for the part.

        Returns:
            str: The unique identifier generated from documentId, documentMicroversion,
                elementId, and fullConfiguration.
        """
        return generate_uid([self.documentId, self.documentMicroversion, self.elementId, self.fullConfiguration])


class Part(IDBase):
    """
    Part data model representing a part in an assembly.

    Example JSON representation:
    {
        "isStandardContent": false,
        "partId": "RDBD",
        "bodyType": "solid",
        "fullConfiguration": "default",
        "configuration": "default",
        "documentId": "a1c1addf75444f54b504f25c",
        "elementId": "0b0c209535554345432581fe",
        "documentMicroversion": "349f6413cafefe8fb4ab3b07"
    }

    Attributes:
        isStandardContent (bool): Indicates if the part is standard content.
        partId (str): The unique identifier of the part.
        bodyType (str): The type of the body (e.g., solid, surface).
        MassProperty (Union[MassProperties, None]): The mass properties of the part, if available.
    """

    isStandardContent: bool = Field(..., description="Indicates if the part is standard content.")
    partId: str = Field(..., description="The unique identifier of the part.")
    bodyType: str = Field(..., description="The type of the body (e.g., solid, surface).")
    MassProperty: Union[MassProperties, None] = Field(
        None, description="The mass properties of the part, if available."
    )

    @property
    def uid(self) -> str:
        """
        Generates a unique identifier for the part.

        Returns:
            str: The unique identifier generated from documentId, documentMicroversion,
                elementId, partId, and fullConfiguration.
        """
        return generate_uid([
            self.documentId,
            self.documentMicroversion,
            self.elementId,
            self.partId,
            self.fullConfiguration,
        ])


class PartInstance(IDBase):
    """
    Part Instance model
    {
        "isStandardContent" : false,
        "type" : "Part",
        "id" : "M0Cyvy+yIq8Rd7En0",
        "name" : "Part 1 <2>",
        "suppressed" : false,
        "partId" : "JHD",

        "fullConfiguration" : "default",
        "configuration" : "default",
        "documentId" : "a1c1addf75444f54b504f25c",
        "elementId" : "a86aaf34d2f4353288df8812",
        "documentMicroversion" : "12fabf866bef5a9114d8c4d2"
    }
    """

    isStandardContent: bool
    type: INSTANCE_TYPE
    id: str
    name: str
    suppressed: bool
    partId: str

    @field_validator("type")
    def check_type(cls, v: INSTANCE_TYPE) -> INSTANCE_TYPE:
        if v != INSTANCE_TYPE.PART:
            raise ValueError("Type must be Part")

        return v

    @property
    def uid(self) -> str:
        return generate_uid([
            self.documentId,
            self.documentMicroversion,
            self.elementId,
            self.partId,
            self.fullConfiguration,
        ])


class AssemblyInstance(IDBase):
    """
    Assembly Instance model
    {
        "id" : "Mon18P7LPP8A9STk+",
        "type" : "Assembly",
        "name" : "subAssembly <1>",
        "suppressed" : false,

        "fullConfiguration" : "default",
        "configuration" : "default",
        "documentId" : "a1c1addf75444f54b504f25c",
        "elementId" : "f0b3a4afab120f778a4037df",
        "documentMicroversion" : "349f6413cafefe8fb4ab3b07"
    }
    """

    id: str
    type: INSTANCE_TYPE
    name: str
    suppressed: bool

    @field_validator("type")
    def check_type(cls, v: INSTANCE_TYPE) -> INSTANCE_TYPE:
        if v != INSTANCE_TYPE.ASSEMBLY:
            raise ValueError("Type must be Assembly")

        return v


class MatedCS(BaseModel):
    """
    Mated CS model
    {
        "xAxis" : [ 1.0, 0.0, 0.0 ],
        "yAxis" : [ 0.0, 0.0, -1.0 ],
        "zAxis" : [ 0.0, 1.0, 0.0 ],
        "origin" : [ 0.0, -0.0505, 0.0 ]
    }
    """

    xAxis: list[float]
    yAxis: list[float]
    zAxis: list[float]
    origin: list[float]

    @field_validator("xAxis", "yAxis", "zAxis", "origin")
    def check_vectors(cls, v: list[float]) -> list[float]:
        if len(v) != 3:
            raise ValueError("Vectors must have 3 values")

        return v

    @property
    def part_to_mate_tf(self) -> np.matrix:
        rotation_matrix = np.array([self.xAxis, self.yAxis, self.zAxis]).T
        translation_vector = np.array(self.origin)
        part_to_mate_tf = np.eye(4)
        part_to_mate_tf[:3, :3] = rotation_matrix
        part_to_mate_tf[:3, 3] = translation_vector
        return np.matrix(part_to_mate_tf)


class MatedEntity(BaseModel):
    """
    MatedEntity data model
    {
        "matedOccurrence" : [ "MDUJyqGNo7JJll+/h" ],
        "matedCS" :
        {
            "xAxis" : [ 1.0, 0.0, 0.0 ],
            "yAxis" : [ 0.0, 0.0, -1.0 ],
            "zAxis" : [ 0.0, 1.0, 0.0 ],
            "origin" : [ 0.0, -0.0505, 0.0 ]
        }
    }
    """

    matedOccurrence: list[str]
    matedCS: MatedCS


class MateRelationMate(BaseModel):
    """
    {
        "featureId": "S4/TgCRmQt1nIHHp",
        "occurrence": []
    },
    """

    featureId: str
    occurrence: list[str]


class MateGroupFeatureOccurrence(BaseModel):
    occurrence: list[str]


class MateGroupFeatureData(BaseModel):
    occurrences: list[MateGroupFeatureOccurrence]
    name: str


class MateConnectorFeatureData(BaseModel):
    """
    {
        "mateConnectorCS": {
            "xAxis": [],
            "yAxis": [],
            "zAxis": [],
            "origin": []
        },
        "occurrence": [
            "MplKLzV/4d+nqmD18"
        ],
        "name": "Mate connector 1"
    }
    """

    mateConnectorCS: MatedCS
    occurrence: list[str]
    name: str


class MateRelationFeatureData(BaseModel):
    """
    {
        "relationType": "GEAR",
        "mates": [
            {
            "featureId": "S4/TgCRmQt1nIHHp",
            "occurrence": []
            },
            {
            "featureId": "QwaoOeXYPifsN7CP",
            "occurrence": []
            }
        ],
        "reverseDirection": false,
        "relationRatio": 1,
        "name": "Gear 1"
    }
    """

    relationType: RELATION_TYPE
    mates: list[MateRelationMate]
    reverseDirection: bool
    relationRatio: Union[float, None] = None
    name: str


class MateFeatureData(BaseModel):
    """
    MateFeatureData data model
    {
        "matedEntities" :
        [
            {
                "matedOccurrence" : [ "MDUJyqGNo7JJll+/h" ],
                "matedCS" :
                {
                    "xAxis" : [ 1.0, 0.0, 0.0 ],
                    "yAxis" : [ 0.0, 0.0, -1.0 ],
                    "zAxis" : [ 0.0, 1.0, 0.0 ],
                    "origin" : [ 0.0, -0.0505, 0.0 ]
                }
            }, {
                "matedOccurrence" : [ "MwoBIsds8rn1/0QXA" ],
                "matedCS" :
                {
                    "xAxis" : [ 0.8660254037844387, 0.0, -0.49999999999999994 ],
                    "yAxis" : [ -0.49999999999999994, 0.0, -0.8660254037844387 ],
                    "zAxis" : [ 0.0, 1.0, 0.0 ],
                    "origin" : [ 0.0, -0.0505, 0.0 ]
                }
            }
        ],
        "mateType" : "FASTENED",
        "name" : "Fastened 1"
    }
    """

    matedEntities: list[MatedEntity]
    mateType: MATE_TYPE
    name: str


class AssemblyFeature(BaseModel):
    id: str
    suppressed: bool
    featureType: ASSEMBLY_FEATURE_TYPE
    featureData: Union[MateGroupFeatureData, MateConnectorFeatureData, MateRelationFeatureData, MateFeatureData]


class Pattern(BaseModel):
    pass


class SubAssembly(IDBase):
    """
    SubAssembly data model
    """

    instances: list[Union[PartInstance, AssemblyInstance]]
    patterns: list[Pattern]
    features: list[AssemblyFeature]

    @property
    def uid(self) -> str:
        return generate_uid([self.documentId, self.documentMicroversion, self.elementId, self.fullConfiguration])


class RootAssembly(SubAssembly):
    """
    RootAssembly data model
    """

    occurrences: list[Occurrence]


class Assembly(BaseModel):
    """
    Assembly data model
    """

    rootAssembly: RootAssembly
    subAssemblies: list[SubAssembly]
    parts: list[Part]
    partStudioFeatures: list[dict]

    document: Union[Document, None] = None
