from enum import Enum
from typing import Any, cast

import regex as re
from pydantic import BaseModel, field_validator, model_validator

__all__ = ["WORKSPACE_TYPE", "Document", "parse_url"]


class WORKSPACE_TYPE(Enum):
    def __str__(self):
        return str(self.value)

    W = "w"
    V = "v"
    M = "m"


DOCUMENT_PATTERN = r"https://cad.onshape.com/documents/([\w\d]+)/(w|v|m)/([\w\d]+)/e/([\w\d]+)"
WORKSPACE_TYPES = [member.value for member in WORKSPACE_TYPE]


def parse_url(url: str) -> str:
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
    url: str
    did: str = None
    wtype: str = None
    wid: str = None
    eid: str = None

    @model_validator(mode="before")
    def set_identifiers(cls, values: dict[str, Any]) -> dict[str, Any]:
        did, wtype, wid, eid = parse_url(values["url"])

        values["did"] = values.get("did") or did
        values["wtype"] = values.get("wtype") or wtype
        values["wid"] = values.get("wid") or wid
        values["eid"] = values.get("eid") or eid

        return values

    @field_validator("did", "wid", "eid")
    def validate_did(cls, value: str) -> str:
        if not value:
            raise ValueError("ID cannot be empty, please check the URL")
        if not len(value) == 24:
            raise ValueError("ID must be 24 characters long, please check the URL")
        return value

    @field_validator("wtype")
    def validate_wtype(cls, value: str) -> str:
        if not value:
            raise ValueError("Workspace type cannot be empty, please check the URL")

        if value not in WORKSPACE_TYPES:
            raise ValueError(f"Invalid workspace type. Must be one of {WORKSPACE_TYPES}, please check the URL")

        return value


if __name__ == "__main__":
    doc = Document(
        url="https://cad.onshape.com/documents/a1c1addf75444f54b504f25c/w/0d17b8ebb2a4c76be9fff3c7/e/a86aaf34d2f4353288df8812"
    )
    print(doc.did)
