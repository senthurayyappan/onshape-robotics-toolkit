"""
This module defines data model for elements retrieved from Onshape REST API responses.

The data models are implemented as Pydantic BaseModel classes, which are used to

    1. Parse JSON responses from the API into Python objects.
    2. Validate the structure and types of the JSON responses.
    3. Provide type hints for better code clarity and autocompletion.

These models ensure that the data received from the API adheres to the expected format and types, facilitating easier
and safer manipulation of the data within the application.

Models:
    - **Element**: Represents an Onshape element, containing the element ID, name, type, and microversion ID.

Enums:
    - **ELEMENT_TYPE**: Enumerates the possible element types in Onshape (PARTSTUDIO, ASSEMBLY, DRAWING, etc.).
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

__all__ = ["ELEMENT_TYPE", "Element"]


class ELEMENT_TYPE(str, Enum):
    """
    Enumerates the possible element types in Onshape

    Attributes:
        PARTSTUDIO: Part Studio
        ASSEMBLY: Assembly
        VARIABLESTUDIO: Variable Studio
        DRAWING: Drawing
        BILLOFMATERIALS: Bill of Materials
        APPLICATION: Application
        BLOB: Blob
        FEATURESTUDIO: Feature Studio
    """

    PARTSTUDIO = "PARTSTUDIO"
    ASSEMBLY = "ASSEMBLY"
    VARIABLESTUDIO = "VARIABLESTUDIO"
    DRAWING = "DRAWING"
    BILLOFMATERIALS = "BILLOFMATERIALS"
    APPLICATION = "APPLICATION"
    BLOB = "BLOB"
    FEATURESTUDIO = "FEATURESTUDIO"


class Element(BaseModel):
    """
    Represents an Onshape element, containing the element ID, name, type, and microversion ID.

    JSON:
        ```json
            {
                "name": "wheelAndFork",
                "id": "0b0c209535554345432581fe",
                "type": "Part Studio",
                "elementType": "PARTSTUDIO",
                "dataType": "onshape/partstudio",
                "microversionId": "9b3be6165c7a2b1f6dd61305",
                "lengthUnits": "millimeter",
                "angleUnits": "degree",
                "massUnits": "kilogram",
                "timeUnits": "second",
                "forceUnits": "newton",
                "pressureUnits": "pascal",
                "momentUnits": "newtonMeter",
                "accelerationUnits": "meterPerSecondSquared",
                "angularVelocityUnits": "degreePerSecond",
                "energyUnits": "footPoundForce",
                "areaUnits": "squareMillimeter",
                "volumeUnits": "cubicMillimeter",
            }
        ```

    Attributes:
        id (str): The unique identifier of the element.
        name (str): The name of the element.
        elementType (str): The type of the element (e.g., PARTSTUDIO, ASSEMBLY, DRAWING).
        microversionId (str): The unique identifier of the microversion of the element.
    """

    id: str = Field(..., description="The unique identifier of the element")
    name: str = Field(..., description="The name of the element")
    elementType: str = Field(..., description="The type of the element")
    microversionId: str = Field(..., description="The unique identifier of the microversion of the element")

    @field_validator("elementType")
    def validate_type(cls, value: str) -> str:
        """
        Validate the element type.

        Args:
            value (str): The element type to validate.

        Returns:
            str: The validated element type.

        Raises:
            ValueError: If the element type is not one of the valid types.
        """

        if value not in ELEMENT_TYPE.__members__.values():
            raise ValueError(f"Invalid element type: {value}")

        return value

    @field_validator("id")
    def validate_id(cls, value: str) -> str:
        """
        Validate the element ID.

        Args:
            value (str): The element ID to validate.

        Returns:
            str: The validated element ID.

        Raises:
            ValueError: If the element ID is not 24 characters long.
        """

        if len(value) != 24:
            raise ValueError(f"Invalid element ID: {value}, must be 24 characters long")

        return value

    @field_validator("microversionId")
    def validate_mid(cls, value: str) -> str:
        """
        Validate the microversion ID.

        Args:
            value (str): The microversion ID to validate.

        Returns:
            str: The validated microversion ID.

        Raises:
            ValueError: If the microversion ID is not 24 characters long.
        """

        if len(value) != 24:
            raise ValueError(f"Invalid microversion ID: {value}, must be 24 characters long")

        return value
