"""Build the student, solution and rubric PDFs of one LaTeX document.

One .tex source carries all three copies.  The \\sol and \\rub macros mark
what only the answer key and the rubric show, \\stud what only the student
copy shows, and each build is a pdflatex run defining \\showsol, \\showrub
or neither.  The flags are deliberately not named \\sol and \\rub: a
document cannot both define a macro and test whether it is defined, and
the collision would silently leak answers onto the student copy.

All three are built unless --no-sol or --no-rub refuses one, or the
document carries none of that content, in which case the copy would only
duplicate another and is skipped (see uses_macro).

Command-line arguments are files, globs or directories, resolved here
rather than left to the shell, so quiz1* reaches quiz1a and quiz1b on
every platform.
"""

import glob
import os
import pathlib
import re
import subprocess
from collections.abc import Iterator
from typing import Optional

DOCUMENTCLASS = re.compile(r'^\s*\\documentclass', re.MULTILINE)

INPUT = re.compile(r'\\input\{([^}]*)\}')

# Names of the content macros, overridable through [macros] in pset.toml
# for a repo that calls them something else.
MACROS_DEFAULT = {'sol': 'sol', 'rub': 'rub'}


def build_pdf(path: pathlib.Path, jobname: str = None, sol: bool = False,
              rub: bool = False, clean: bool = True,
              quiet: bool = True) -> pathlib.Path:
    """Run pdflatex on one document.

    Args:
        path: the .tex file, suffix optional
        jobname: output basename, defaults to the input's
        sol: define \\showsol, revealing the answers
        rub: define \\showrub, revealing the rubric (needs sol too)
        clean: delete the aux, out and log files afterwards.  A failed
            run keeps them either way, since the log holds the error.
        quiet: swallow the pdflatex transcript.  The error survives on
            the raised exception, so nothing is lost on a failure.

    Returns:
        pdf: the file written

    Raises:
        subprocess.CalledProcessError: pdflatex rejected the document
    """
    path = pathlib.Path(path).with_suffix('')

    # nonstopmode so a broken document reports and exits rather than
    # stopping for input, which would strand a whole batch of builds.
    command = ['pdflatex', '-interaction=nonstopmode']
    if jobname:
        command += ['--jobname', jobname]
    if sol and rub:
        command += ['\\def\\showsol{1} \\def\\showrub{1} '
                    '\\input{' + path.name + '}']
    elif sol:
        command += ['\\def\\showsol{1} \\input{' + path.name + '}']
    else:
        command += [path.name]

    subprocess.run(command, check=True, cwd=path.parent,
                   capture_output=quiet, text=True)

    if clean:
        clean_up(path)

    return path.parent / f'{jobname or path.name}.pdf'


def latex_error(transcript: str, lines: int = 12) -> str:
    """Pull the failure out of a pdflatex transcript.

    Args:
        transcript: everything pdflatex printed
        lines: how much to keep once the failure is found

    Returns:
        excerpt: from the first line pdflatex marked with '!', which
            carries the message and the source line it died on.  The tail
            of the transcript if nothing is marked, since a failure that
            does not name itself is still worth seeing.
    """
    text = transcript.splitlines()
    for index, line in enumerate(text):
        if line.startswith('!'):
            return '\n'.join(text[index:index + lines])
    return '\n'.join(text[-lines:])


def clean_up(path: pathlib.Path) -> None:
    """Delete the aux, out and log files of a document's three builds."""
    for stem in [path.stem, f'{path.stem}_sol', f'{path.stem}_rub']:
        for ext in ['aux', 'out', 'log']:
            (path.parent / f'{stem}.{ext}').unlink(missing_ok=True)


def is_document(path: pathlib.Path) -> bool:
    """Report whether a .tex file is a whole document, not a fragment."""
    return bool(DOCUMENTCLASS.search(path.read_text(errors='ignore')))


def uses_macro(path: pathlib.Path, macro: str) -> Optional[bool]:
    """Report whether a document uses a macro, following its \\input tree.

    The content macros live in the problem files a document pulls in
    rather than in the document itself, so the whole tree has to be read:
    an exam naming no \\rub of its own may still input eight problems
    that do.

    Args:
        path: the .tex file
        macro: the name without its backslash, e.g. rub

    Returns:
        used: True if found.  None where the tree could not be read to
            the end, either a missing file or an \\input whose path is
            assembled from a macro, since a document that might use it
            has to be built anyway.  False only when the whole tree was
            read and the macro is absent from all of it.
    """
    use = re.compile(rf'\\{macro}\s*\{{')
    path = pathlib.Path(path)

    # Every \input resolves against the folder pdflatex runs in, which is
    # the document's own, and nesting does not move that base: an \input
    # inside a repo-root command.tex is still read relative to hw1/, not
    # to command.tex.  Resolving against the including file instead
    # happens to agree for hw1/hw1.tex naming ../packages.tex, and
    # disagrees the moment a file one level up does the naming.
    base = path.parent

    seen, stack = set(), [path]
    found = blind = False
    while stack:
        current = stack.pop()
        if not current.suffix:
            current = current.with_suffix('.tex')
        current = pathlib.Path(os.path.normpath(current))
        if current in seen:
            continue
        seen.add(current)
        if not current.is_file():
            blind = True
            continue
        text = current.read_text(errors='ignore')
        found = found or bool(use.search(text))
        for target in INPUT.findall(text):
            if '\\' in target:
                blind = True
            else:
                stack.append(base / target)

    if found:
        return True
    return None if blind else False


def expand(pattern: str) -> Iterator[pathlib.Path]:
    """Yield the candidate files one command-line argument names.

    A pattern the shell already expanded arrives as a plain path and passes
    through; one it left alone is globbed here.  A directory stands for the
    .tex files directly inside it.
    """
    for match in sorted(glob.glob(pattern)) or [pattern]:
        path = pathlib.Path(match)
        if path.is_dir():
            yield from sorted(path.glob('*.tex'))
        else:
            yield path


def resolve(patterns: list[str]) -> list[pathlib.Path]:
    """Map command-line arguments onto the .tex files to build.

    Args:
        patterns: paths, globs or directories, .tex suffix optional

    Returns:
        paths: the .tex files, deduplicated, in the order named.  A
            pattern matching several files keeps only the whole documents
            among them; a file named on its own is built whatever it holds.

    Raises:
        FileNotFoundError: a pattern matches nothing on disk
    """
    paths = []
    for pattern in patterns:
        candidates = list(expand(pattern))
        found = []
        for candidate in candidates:
            tex = candidate.with_suffix('.tex')
            if tex.is_file() and tex not in found:
                found.append(tex)
        if len(found) > 1:
            found = [tex for tex in found if is_document(tex)]
        if not found:
            # An existing file with no source of its own is a build the
            # shell swept in beside it (quiz1a_sol.pdf), so drop it
            # quietly; a name matching nothing at all is a typo.
            if not any(candidate.exists() for candidate in candidates):
                raise FileNotFoundError(
                    f'no document to build matches: {pattern}')
            continue
        paths += [tex for tex in found if tex not in paths]
    return paths
