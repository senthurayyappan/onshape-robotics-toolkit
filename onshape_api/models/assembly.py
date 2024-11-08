from enum import Enum
from typing import Literal, Union

import numpy as np
from pydantic import BaseModel, Field, field_validator

from onshape_api.models.document import Document
from onshape_api.models.mass import MassProperties
from onshape_api.utilities.helpers import generate_uid


class INSTANCE_TYPE(str, Enum):
    PART = "Part"
    ASSEMBLY = "Assembly"


class MATE_TYPE(str, Enum):
    SLIDER = "SLIDER"
    CYLINDRICAL = "CYLINDRICAL"
    REVOLUTE = "REVOLUTE"
    PIN_SLOT = "PIN_SLOT"
    PLANAR = "PLANAR"
    BALL = "BALL"
    FASTENED = "FASTENED"
    PARALLEL = "PARALLEL"


class RELATION_TYPE(str, Enum):
    LINEAR = "LINEAR"
    GEAR = "GEAR"
    SCREW = "SCREW"
    RACK_AND_PINION = "RACK_AND_PINION"


class ASSEMBLY_FEATURE_TYPE(str, Enum):
    MATE = "mate"
    MATERELATION = "mateRelation"
    MATEGROUP = "mateGroup"
    MATECONNECTOR = "mateConnector"


class Occurrence(BaseModel):
    """
    Occurence model

    {
    "fixed" : false,
    "transform" :
        [ 0.8660254037844396, 0.0, 0.5000000000000004, 0.09583333333333346,
        0.0, 1.0, 0.0, -1.53080849893419E-19,
        -0.5000000000000004, 0.0, 0.8660254037844396, 0.16598820239201767,
        0.0, 0.0, 0.0, 1.0 ],
    "hidden" : false,
    "path" : [ "M0Cyvy+yIq8Rd7En0" ]
    }
    """

    fixed: bool
    transform: list[float]
    hidden: bool
    path: list[str]

    @field_validator("transform")
    def check_transform(cls, v: list[float]) -> list[float]:
        if len(v) != 16:
            raise ValueError("Transform must have 16 values")

        return v


class IDBase(BaseModel):
    """
    Base model for Part in Assembly context
    {
        "fullConfiguration" : "default",
        "configuration" : "default",
        "documentId" : "a1c1addf75444f54b504f25c",
        "elementId" : "0b0c209535554345432581fe",
        "documentMicroversion" : "12fabf866bef5a9114d8c4d2"
    }
    """

    fullConfiguration: str
    configuration: str
    documentId: str
    elementId: str
    documentMicroversion: str

    @field_validator("documentId", "elementId", "documentMicroversion")
    def check_ids(cls, v: str) -> str:
        if len(v) != 24:
            raise ValueError("DocumentId must have 24 characters")

        return v

    @property
    def uid(self) -> str:
        return generate_uid([self.documentId, self.documentMicroversion, self.elementId, self.fullConfiguration])


class Part(IDBase):
    """
    Part data model
    {
      "isStandardContent" : false,
      "partId" : "RDBD",
      "bodyType" : "solid",

      "fullConfiguration" : "default",
      "configuration" : "default",
      "documentId" : "a1c1addf75444f54b504f25c",
      "elementId" : "0b0c209535554345432581fe",
      "documentMicroversion" : "349f6413cafefe8fb4ab3b07"
    }
    """

    isStandardContent: bool
    partId: str
    bodyType: str
    MassProperty: Union[MassProperties, None] = None

    @property
    def uid(self) -> str:
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


Instance = Union[PartInstance, AssemblyInstance]


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


class BaseAssemblyFeature(BaseModel):
    featureType: str


class MateFeature(BaseAssemblyFeature):
    """
    Feature model
    {
        "id" : "M11CFUi4PcoWOBxpJ",
        "suppressed" : false,
        "featureType" : "mate",
        "featureData" :
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
    }
    """

    id: str
    suppressed: bool
    featureType: Literal["MateFeature"] = "MateFeature"
    featureData: MateFeatureData


class MateRelationMate(BaseModel):
    """
    {
        "featureId": "S4/TgCRmQt1nIHHp",
        "occurrence": []
    },
    """

    featureId: str
    occurrence: list[str]


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
    relationRatio: float
    name: str


class MateRelationFeature(BaseAssemblyFeature):
    """
    {
        "id": "amcpeia1Lm2LN2He",
        "suppressed": false,
        "featureType": "mateRelation",
        "featureData":
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
    },
    """

    id: str
    suppressed: bool
    featureType: Literal["MateRelationFeature"] = "MateRelationFeature"
    featureData: MateRelationFeatureData


class MateGroupFeatureOccurrence(BaseModel):
    occurrence: list[str]


class MateGroupFeatureData(BaseModel):
    occurrences: list[MateGroupFeatureOccurrence]
    name: str


class MateGroupFeature(BaseAssemblyFeature):
    id: str
    suppressed: bool
    featureType: Literal["MateGroupFeature"] = "MateGroupFeature"
    featureData: MateGroupFeatureData


class MateConnectorFeatureData(BaseModel):
    mateConnectorCS: MatedCS
    occurence: list[str]
    name: str


class MateConnectorFeature(BaseAssemblyFeature):
    """
    {
        "id": "MftzXroqpwJJDurRm",
        "suppressed": false,
        "featureType": "mateConnector",
        "featureData": {
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
    },
    """

    id: str
    suppressed: bool
    featureType: Literal["MateConnectorFeature"] = "MateConnectorFeature"
    featureData: MateConnectorFeatureData


class Pattern(BaseModel):
    pass


class SubAssembly(IDBase):
    """
    SubAssembly data model
    """

    instances: list[Union[PartInstance, AssemblyInstance]]
    patterns: list[Pattern]
    features: list[Union[MateFeature, MateRelationFeature, MateGroupFeature, MateConnectorFeature]] = Field(
        ..., discriminator="featureType"
    )

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
