"""
This module contains utility functions used across the Onshape API package.

Functions:
    - **xml_escape**: Escape XML characters in a string.
    - **format_number**: Format a number to 8 significant figures.
    - **generate_uid**: Generate a 16-character unique identifier from a list of strings.
    - **print_dict**: Print a dictionary with indentation for nested dictionaries.
    - **get_random_files**: Get random files from a directory with a specific file extension and count.
    - **get_random_names**: Generate random names from a list of words in a file.
"""

import hashlib
import json
import os
import random
from xml.sax.saxutils import escape

from pydantic import BaseModel

from onshape_api.log import LOGGER


def save_model_as_json(model: BaseModel, file_path: str) -> None:
    """
    Save a Pydantic model as a JSON file

    Args:
        model (BaseModel): Pydantic model to save
        file_path (str): File path to save JSON file

    Returns:
        None

    Examples:
        >>> class TestModel(BaseModel):
        ...     a: int
        ...     b: str
        ...
        >>> save_model_as_json(TestModel(a=1, b="hello"), "test.json")
    """

    with open(file_path, "w") as file:
        json.dump(model.model_dump(), file, indent=4)


def xml_escape(unescaped: str) -> str:
    """
    Escape XML characters in a string

    Args:
        unescaped (str): Unescaped string

    Returns:
        str: Escaped string

    Examples:
        >>> xml_escape("hello 'world' \"world\"")
        "hello &apos;world&apos; &quot;world&quot;"

        >>> xml_escape("hello <world>")
        "hello &lt;world&gt;"
    """

    return escape(unescaped, entities={"'": "&apos;", '"': "&quot;"})


def format_number(value: float) -> str:
    """
    Format a number to 8 significant figures

    Args:
        value (float): Number to format

    Returns:
        str: Formatted number

    Examples:
        >>> format_number(0.123456789)
        "0.12345679"

        >>> format_number(123456789)
        "123456789"
    """

    return f"{value:.8g}"


def generate_uid(values: list[str]) -> str:
    """
    Generate a 16-character unique identifier from a list of strings

    Args:
        values (list[str]): List of strings to concatenate

    Returns:
        str: Unique identifier

    Examples:
        >>> generate_uid(["hello", "world"])
        "c4ca4238a0b92382"
    """

    _value = "".join(values)
    return hashlib.sha256(_value.encode()).hexdigest()[:16]


def print_dict(d: dict, indent=0) -> None:
    """
    Print a dictionary with indentation for nested dictionaries

    Args:
        d (dict): Dictionary to print
        indent (int): Number of tabs to indent

    Returns:
        None

    Examples:
        >>> print_dict({"a": 1, "b": {"c": 2}})
        a
            1
        b
            c
                2
    """

    for key, value in d.items():
        print()
        print("\t" * indent + str(key))
        if isinstance(value, dict):
            print_dict(value, indent + 1)
        else:
            print("\t" * (indent + 1) + str(value))


def get_random_files(directory: str, file_extension: str, count: int) -> list[str]:
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

    Examples:
        >>> get_random_files("json", ".json", 1)
        ["json/file.json"]

        >>> get_random_files("json", ".json", 2)
        ["json/file1.json", "json/file2.json"]
    """

    _files = [file for file in os.listdir(directory) if file.endswith(file_extension)]

    if len(_files) < count:
        raise ValueError("Not enough files in directory")

    selected_files = random.sample(_files, count)
    file_paths = [os.path.join(directory, file) for file in selected_files]

    LOGGER.info(f"Selected files: {file_paths}")

    return file_paths, [x.split(".")[0] for x in selected_files]


def get_random_names(directory: str, count: int, filename: str = "words.txt") -> list[str]:
    """
    Generate random names from a list of words in a file

    Args:
        directory: Path to directory containing words file
        count: Number of random names to generate
        filename: File containing list of words. Default is "words.txt"

    Returns:
        List of random names

    Raises:
        ValueError: If count exceeds the number of available words

    Examples:
        >>> get_random_names(directory="../", count=1)
        ["charizard"]

        >>> get_random_names(directory="../", count=2)
        ["charizard", "pikachu"]
    """

    words_file_path = os.path.join(directory, filename)

    with open(words_file_path) as file:
        words = file.read().splitlines()

    if count > len(words):
        raise ValueError("count exceeds the number of available words")

    return random.sample(words, count)


def get_sanitized_name(name: str, replace_with: str = "-") -> str:
    """
    Sanitize a name by removing special characters, preserving "-" and "_", and
    replacing spaces with a specified character.

    Args:
        name: Name to sanitize
        replace_with: Character to replace spaces with (default is '-')

    Returns:
        Sanitized name

    Examples:
        >>> get_sanitized_name("wheel1 <3>", '-')
        "wheel1-3"
        >>> get_sanitized_name("Hello World!", '_')
        "Hello_World"
    """

    if replace_with not in "-_":
        raise ValueError("replace_with must be either '-' or '_'")

    sanitized_name = "".join(char if char.isalnum() or char in "-_ " else "" for char in name)
    return sanitized_name.replace(" ", replace_with)


if __name__ == "__main__":
    LOGGER.info(get_sanitized_name(input("Enter a name: ")))
