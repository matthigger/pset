#!/usr/bin/env python3
"""Build the student, solution and rubric PDFs of a LaTeX assignment.

One .tex source carries all three copies: the \\sol and \\rub macros mark
the parts only the answer key and the grading rubric should show, and each
copy is a pdflatex run that defines a different subset of them.  All three
are built unless --no-sol or --no-rub says otherwise.

Arguments are files, globs or directories, resolved here rather than left
to the shell, so quiz1* reaches quiz1a and quiz1b on every platform.  Two
filters keep a wide pattern honest: sibling builds (quiz1a.pdf,
quiz1a_sol.pdf) collapse onto the .tex they came from, and a fragment with
no \\documentclass, e.g. reminder.tex, is skipped.
"""

import argparse
import glob
import importlib.util
import pathlib
import re
import subprocess
import sys
from collections.abc import Iterator

__version__ = '0.1.0'

DOCUMENTCLASS = re.compile(r'^\s*\\documentclass', re.MULTILINE)


def build_pdf(path: pathlib.Path, jobname: str = None, sol: bool = False,
              rub: bool = False, clean: bool = True) -> None:
    """Run pdflatex on one document.

    Args:
        path: the .tex file, suffix optional
        jobname: output basename, defaults to the input's
        sol: define \\sol, revealing the answers
        rub: define \\rub, revealing the rubric (needs sol too)
        clean: delete the aux, out and log files afterwards.  A failed
            run keeps them either way, since the log holds the error.

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
        command += ['\\def\\sol{1} \\def\\rub{1} \\input{' + path.name + '}']
    elif sol:
        command += ['\\def\\sol{1} \\input{' + path.name + '}']
    else:
        command += [path.name]

    subprocess.run(command, check=True, cwd=path.parent)

    if clean:
        clean_up(path)


def sum_points(path: pathlib.Path) -> None:
    """Print the point total of a document.

    Raises:
        SystemExit: the optional sum-pts dependency is not installed
    """
    if importlib.util.find_spec('sum_pts') is None:
        sys.exit('summing points needs sum-pts: pip install "solrub[pts]"')

    command = [
        sys.executable, '-m', 'sum_pts', f"{path}",
        '--left', '\\[', '--right', '\\]',
        '--points', 'pts?', '--prefix', ' *\\\\prob',
        '-r', '\\(\\d+.?\\d* each\\)',
        '-r', '\\((\\d+.?\\d*,? ?)+\\)',
        '-r', '\\{', '-r', '\\}', '-r', ':'
    ]
    subprocess.run(command, check=True)


def clean_up(path: pathlib.Path) -> None:
    """Delete the aux, out and log files of a document's three builds."""
    for stem in [path.stem, f'{path.stem}_sol', f'{path.stem}_rub']:
        for ext in ['aux', 'out', 'log']:
            (path.parent / f'{stem}.{ext}').unlink(missing_ok=True)


def is_document(path: pathlib.Path) -> bool:
    """Report whether a .tex file is a whole document, not a fragment."""
    return bool(DOCUMENTCLASS.search(path.read_text(errors='ignore')))


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


def main() -> None:
    """Run the command line interface."""
    parser = argparse.ArgumentParser(
        prog='solrub',
        description='Build the student, solution and rubric PDFs of a '
                    'LaTeX assignment.')
    parser.add_argument('-s', '--sol', action=argparse.BooleanOptionalAction,
                        default=True, help='build solution copy')
    parser.add_argument('-r', '--rub', action=argparse.BooleanOptionalAction,
                        default=True, help='build rubric copy')
    parser.add_argument('-p', '--pts', action='store_true', help='sum points')
    parser.add_argument('-V', '--version', action='version',
                        version=f'%(prog)s {__version__}')
    parser.add_argument('path', nargs='+',
                        help='.tex files, globs or directories to build')

    args = parser.parse_args()

    failed = []
    for path in resolve(args.path):
        print(f'==> {path}', flush=True)

        # One unbuildable document must not strand the rest of the batch,
        # so collect the failures and report them together at the end.
        try:
            build_pdf(path)

            if args.sol:
                build_pdf(path, jobname=f'{path.stem}_sol', sol=True)

            if args.rub:
                build_pdf(path, jobname=f'{path.stem}_rub', sol=True,
                          rub=True)

            if args.pts:
                sum_points(path)
        except subprocess.CalledProcessError:
            failed.append(path)

    if failed:
        names = ', '.join(str(path) for path in failed)
        sys.exit(f'failed: {names}\nthe .log beside each holds the error')


if __name__ == "__main__":
    main()
