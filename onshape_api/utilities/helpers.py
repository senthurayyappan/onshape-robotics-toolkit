import hashlib
import os
import random
from xml.sax.saxutils import escape

from onshape_api.log import LOGGER


def xml_escape(unescaped: str) -> str:
    """
    Escape XML characters in a string

    Args:
        unescaped (str): Unescaped string

    Returns:
        str: Escaped string

    Raises:
        None

    Usage:
    >>> xml_escape("hello 'world' \"world\"")
    "hello &apos;world&apos; &quot;world&quot;"

    """
    return escape(unescaped, entities={"'": "&apos;", '"': "&quot;"})

def format_number(value: float) -> str:
    """
    Format a number to 8 significant figures

    Args:
        value (float): Number to format

    Returns:
        str: Formatted number

    Raises:
        None

    Usage:
    >>> format_number(0.123456789)
    "0.12345679"

    """
    return f"{value:.8g}"

def generate_uid(values: list[str]) -> str:
    """
    Generate a 16-character unique identifier from a list of strings

    Args:
        values (list[str]): List of strings to concatenate

    Returns:
        str: Unique identifier

    Raises:
        None

    Usage:
    >>> generate_uid(["hello", "world"])
    "c4ca4238a0b92382"

    """
    _value = "".join(values)
    return hashlib.sha256(_value.encode()).hexdigest()[:16]

def print_dict(d: dict, indent=0):
    """
    Print a dictionary with indentation for nested dictionaries

    Args:
        d (dict): Dictionary to print
        indent (int): Number of tabs to indent

    Returns:
        None

    Raises:
        None

    Usage:
    >>> print_dict({"a": 1, "b": {"c": 2}})
    a
        1
    b
        c
            2

    """
    for key, value in d.items():
        print('\t' * indent + str(key))
        if isinstance(value, dict):
            print_dict(value, indent+1)
        else:
            print('\t' * (indent+1) + str(value))

def get_random_file(directory: str, file_extension: str, count: int) -> list[str]:
    """
    Get random files from a directory with a specific file extension and count

    Args:
        directory (str): Directory path
        file_extension (str): File extension
        count (int): Number of files to select

    Returns:
        list[str]: List of file paths

    Raises:
        ValueError: Not enough files in directory if count exceeds number of files

    Usage:
    >>> get_random_file("json", ".json", 1)
    ["json/file.json"]

    """
    _files = [
        file for file in os.listdir(directory) if file.endswith(file_extension)
    ]

    if len(_files) < count:
        raise ValueError("Not enough files in directory")

    selected_files = random.sample(_files, count)
    file_paths = [os.path.join(directory, file) for file in selected_files]

    LOGGER.info(f"Selected files: {file_paths}")

    return file_paths

if __name__ == "__main__":
    print(get_random_file("json", ".json", 1))
