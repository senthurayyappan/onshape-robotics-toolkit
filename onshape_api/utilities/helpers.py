from xml.sax.saxutils import escape


def xml_escape(unescaped: str) -> str:
    return escape(unescaped, entities={"'": "&apos;", '"': "&quot;"})


def format_number(value: float) -> str:
    return f"{value:.8g}"
