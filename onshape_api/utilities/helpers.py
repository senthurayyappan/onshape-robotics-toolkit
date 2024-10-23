import hashlib
from xml.sax.saxutils import escape


def xml_escape(unescaped: str) -> str:
    return escape(unescaped, entities={"'": "&apos;", '"': "&quot;"})

def format_number(value: float) -> str:
    return f"{value:.8g}"

def generate_uid(values: list[str]) -> str:
    _value = "".join(values)
    return hashlib.sha256(_value.encode()).hexdigest()[:16]
