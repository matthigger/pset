"""Write an example problem repo, and the readme explaining one.

The layout is the whole convention: problems as bodiless .tex fragments
under problems/, grouped by topic, and an assignment beside them that sets
its metadata and inputs the ones it wants.  It is easier to copy than to
describe, so --example writes a working one, five problems and an
assignment that builds all three copies of itself.

README_pset.md is offered separately because a repo may not want one: the
CS1800 repo, say, documents itself already.  The answer is remembered
under the user's config folder, so the question is asked once rather than
on every scaffold.
"""

import pathlib
import shutil
import sys
from importlib.resources import as_file, files
from typing import Optional

from .config import PROBLEMS, README, pref_file, pref_get, pref_set

EXAMPLE = 'pset_example'

# The remembered answer to "write README_pset.md?".  Named for the
# question, not the flag, since --readme asks for one unconditionally.
PREF_README = 'readme'


def ask_readme(default: bool = True) -> bool:
    """Ask whether to write README_pset.md, once, and remember the answer.

    Args:
        default: what an empty reply means

    Returns:
        wanted: the remembered answer where one exists, otherwise what
            the user says now.  The default without asking when stdin is
            not a terminal, since a scripted run has nobody to answer and
            must not block on the prompt.
    """
    remembered = pref_get(PREF_README)
    if remembered is not None:
        return remembered
    if not sys.stdin.isatty():
        return default

    prompt = f'write {README} (how to use pset, for whoever clones this)?'
    suffix = '[Y/n]' if default else '[y/N]'
    try:
        reply = input(f'{prompt} {suffix} ').strip().lower()
    except EOFError:
        reply = ''
    wanted = default if not reply else reply.startswith('y')

    pref_set(PREF_README, wanted)
    print(f'    remembered, change it in {pref_file()}')
    return wanted


def write_readme(root: pathlib.Path, force: bool = False) -> Optional[
        pathlib.Path]:
    """Copy README_pset.md to a repo root, beside its problems folder.

    Args:
        root: the repo root to write into
        force: overwrite an existing copy.  Left False the existing one
            wins, since a repo may have edited it.

    Returns:
        path: the file written, None where one was already there
    """
    out = root / README
    if out.exists() and not force:
        return None
    shutil.copyfile(str(files('pset') / 'data' / README), out)
    return out


def scaffold(out: Optional[pathlib.Path] = None,
             readme: Optional[bool] = None) -> pathlib.Path:
    """Write the example problem repo.

    Args:
        out: the folder to create, defaulting to pset_example/ in the
            working folder
        readme: write README_pset.md, or None to use the remembered
            answer and ask if there is none

    Returns:
        root: the folder written

    Raises:
        FileExistsError: the folder is already there.  Refused rather
            than merged, so a repo that grew from an earlier scaffold is
            never half-overwritten.
    """
    root = pathlib.Path(out or EXAMPLE)
    if root.exists():
        raise FileExistsError(f'{root} exists already, name another folder')

    with as_file(files('pset') / 'data' / 'example') as source:
        shutil.copytree(source, root)

    if readme is None:
        readme = ask_readme()
    if readme:
        write_readme(root)

    count = len(list((root / PROBLEMS).glob('**/*.tex')))
    print(f'wrote {root}/: {count} problems in '
          f'{len(list((root / PROBLEMS).iterdir()))} topics')
    print(f'    cd {root / "hw_example"} && pset hw_example')
    return root
