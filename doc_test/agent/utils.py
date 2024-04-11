import json

from typing import Dict, List, Optional, Tuple, Union

from difflib import get_close_matches
from functools import reduce


class ClassificationError(Exception):
    def __init__(self, response: str, options: List[str]):
        message = f'response "{response}" is not similar enough to any of {options}'
        super().__init__(message)


def classify_output(
    response: str,
    options: Optional[Union[List[str], Dict[str, List[str]]]] = None,
    cutoff: float = 0.5,
) -> str:
    if not options:
        return response
    elif isinstance(options, list):
        matches = get_close_matches(response, options, n=1, cutoff=cutoff)
        if len(matches) == 0:
            raise ClassificationError(response, options)
        return matches[0]
    elif isinstance(options, dict):
        flattened_options = reduce(lambda acc, lst: acc + lst, options.values(), [])
        matches = get_close_matches(response, flattened_options, n=1, cutoff=cutoff)
        if len(matches) == 0:
            raise ClassificationError(response, flattened_options)
        inverse_options = reduce(
            lambda acc, dct: dict(acc, **dct),
            [{value: key for value in options} for key, options in options.items()],
            {},
        )
        return inverse_options[matches[0]]
    else:
        raise ValueError(f"Invalid type for options: {type(options)}")


def update_files_dirs(
    files: List[str],
    dirs: List[str],
    dir_name: str,
    dir_contents: List[Tuple[str, str]],
) -> None:
    new_files = [f"{dir_name}/{file[0]}" for file in dir_contents if file[1] == "file"]
    new_dirs = [f"{dir_name}/{file[0]}" for file in dir_contents if file[1] == "dir"]
    files.extend(new_files)
    dirs.extend(new_dirs)
