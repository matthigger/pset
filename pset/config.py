"""Locate a problem repo, its config file and the remembered preferences.

Three lookups, all of them a walk up the folder tree.  find_repo finds the
root of a problem repo from anywhere inside it, so --browse and --usage
work from a subfolder the way git does.  find_config finds the pset.toml
governing one document.  The preferences live outside any repo, under the
user's config folder, and hold answers to questions worth asking once.
"""

import os
import pathlib
from typing import Optional

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

CONFIG_NAME = 'pset.toml'

# The folder every problem repo keeps its problems in, and the anchor
# find_repo looks for.  A repo not yet holding one is found by its config
# file instead, which is why both are checked.
PROBLEMS = 'problems'

# Where --browse writes, one PDF per topic.  One level under the root, so
# the ../problems/fig.png paths inside the problems still resolve.
BUILD = 'problems_pdf'

README = 'README_pset.md'


class RepoError(Exception):
    """No problem repo was found to work in."""


def find_repo(start: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Find the root of the problem repo holding a path.

    Args:
        start: where to look from, defaulting to the working folder

    Returns:
        root: the folder holding problems/, or failing that the one
            holding a pset.toml, so a repo mid-setup is still found

    Raises:
        RepoError: neither anchor appears anywhere up to the filesystem
            root, meaning the command was run outside a problem repo
    """
    start = pathlib.Path(start or pathlib.Path.cwd()).resolve()
    folders = ([start, *start.parents] if start.is_dir()
               else list(start.parents))

    for folder in folders:
        if (folder / PROBLEMS).is_dir():
            return folder
    for folder in folders:
        if (folder / CONFIG_NAME).is_file():
            return folder

    raise RepoError(
        f'no problem repo around {start}: expected a {PROBLEMS}/ folder '
        f'here or above.  pset --example writes one to start from')


def find_config(path: pathlib.Path) -> dict:
    """Read the pset.toml governing a document.

    Walks up from the document's folder to the filesystem root and takes
    the first file found, so one pset.toml at a problem repo's root
    covers every assignment under it.

    Returns:
        config: the parsed file, empty if the walk finds none
    """
    for folder in path.resolve().parents:
        config = folder / CONFIG_NAME
        if config.is_file():
            with open(config, 'rb') as file:
                return tomllib.load(file)
    return {}


def pref_file() -> pathlib.Path:
    """Give the path of the cross-repo preferences file."""
    root = os.environ.get('XDG_CONFIG_HOME') or '~/.config'
    return pathlib.Path(root).expanduser() / 'pset' / CONFIG_NAME


def pref_get(key: str) -> Optional[bool]:
    """Read one remembered answer.

    Returns:
        answer: None where the question has not been answered yet, which
            is what tells a caller to ask it
    """
    path = pref_file()
    if not path.is_file():
        return None
    try:
        with open(path, 'rb') as file:
            return tomllib.load(file).get(key)
    except (OSError, tomllib.TOMLDecodeError):
        # A preference is a convenience; a corrupt file must not take
        # down the build the user actually asked for.
        return None


def pref_set(key: str, value: bool) -> None:
    """Remember one answer, leaving the others in the file alone."""
    path = pref_file()
    answers = {}
    if path.is_file():
        try:
            with open(path, 'rb') as file:
                answers = tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError):
            answers = {}
    answers[key] = value

    # Writing TOML by hand rather than adding a writer dependency: every
    # value here is a bool, so there is nothing to quote or escape.
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'{name} = {str(bool(answer)).lower()}'
             for name, answer in sorted(answers.items())]
    path.write_text('\n'.join(['# pset preferences', *lines, '']))
