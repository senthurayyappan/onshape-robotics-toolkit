from enum import Enum
from typing import Union, cast

import regex as re
from pydantic import BaseModel, field_validator

__all__ = ["WORKSPACE_TYPE", "Document", "parse_url"]


class WORKSPACE_TYPE(str, Enum):
    W = "w"
    V = "v"
    M = "m"


class META_WORKSPACE_TYPE(str, Enum):
    WORKSPACE = "workspace"
    VERSION = "version"
    MICROVERSION = "microversion"

    @property
    def shorthand(self) -> str:
        return self.value[0]


DOCUMENT_PATTERN = r"https://cad.onshape.com/documents/([\w\d]+)/(w|v|m)/([\w\d]+)/e/([\w\d]+)"


def generate_url(did: str, wtype: str, wid: str, eid: str) -> str:
    return f"https://cad.onshape.com/documents/{did}/{wtype}/{wid}/e/{eid}"


def parse_url(url: str) -> str:
    """
    Parse Onshape URL and return document ID, workspace type, workspace ID, and element ID

    Args:
        url: Onshape URL

    Returns:
        did: Document ID
        wtype: Workspace type
        wid: Workspace ID
        eid: Element ID

    """
    pattern = re.match(
        DOCUMENT_PATTERN,
        url,
    )

    if not pattern:
        raise ValueError("Invalid Onshape URL")

    did = pattern.group(1)
    wtype = cast(WORKSPACE_TYPE, pattern.group(2))
    wid = pattern.group(3)
    eid = pattern.group(4)

    return did, wtype, wid, eid


class Document(BaseModel):
    """
    Data model for Onshape document

    Attributes:
        url: Onshape URL
        did: Document ID
        wtype: Workspace type
        wid: Workspace ID
        eid: Element ID

    """

    url: Union[str, None] = None
    did: str
    wtype: str
    wid: str
    eid: str

    def __init__(self, **data):
        super().__init__(**data)
        if self.url is None:
            self.url = generate_url(self.did, self.wtype, self.wid, self.eid)

    @field_validator("did", "wid", "eid")
    def check_ids(cls, value: str) -> str:
        if not value:
            raise ValueError("ID cannot be empty, please check the URL")
        if not len(value) == 24:
            raise ValueError("ID must be 24 characters long, please check the URL")
        return value

    @field_validator("wtype")
    def check_wtype(cls, value: str) -> str:
        if not value:
            raise ValueError("Workspace type cannot be empty, please check the URL")

        if value not in WORKSPACE_TYPE.__members__.values():
            raise ValueError(
                f"Invalid workspace type. Must be one of {WORKSPACE_TYPE.__members__.values()}, please check the URL"
            )

        return value

    @classmethod
    def from_url(cls, url: str) -> "Document":
        did, wtype, wid, eid = parse_url(url)
        return cls(url=url, did=did, wtype=wtype, wid=wid, eid=eid)


class DefaultWorkspace(BaseModel):
    """
    Data model for Onshape default workspace

    Attributes:
        id: Workspace ID

    """

    id: str
    type: META_WORKSPACE_TYPE


class DocumentMetaData(BaseModel):
    """
    Data model for Onshape document metadata

    Attributes:
        defaultWorkspace: DefaultWorkspace
        name: Document name

    """

    defaultWorkspace: DefaultWorkspace
    name: str
    id: str


if __name__ == "__main__":
    doc = Document(
        url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
    )
    print(doc.did)
