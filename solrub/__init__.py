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

The pdflatex transcript is swallowed unless the run fails or -v asks for
it.  Point counting reads its regexes from a solrub.toml beside the
documents, since how a count is written varies by repo (see find_config).
"""

import argparse
import glob
import importlib.util
import pathlib
import re
import subprocess
import sys
from collections.abc import Iterator

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

__version__ = '0.2.0'

DOCUMENTCLASS = re.compile(r'^\s*\\documentclass', re.MULTILINE)

CONFIG_NAME = 'solrub.toml'

# How a point count is written is a property of the repo, not of this
# tool: [20 pts (8, 12)] and [20 points (6 pts each)] are both in use.
# A [points] table in solrub.toml overrides these per repo.
POINTS_DEFAULT = {
    'left': r'\[',
    'right': r'\]',
    'prefix': r' *\\prob',
    'points': 'pts?',
    'remove': [r'\(\d+.?\d* each\)', r'\((\d+.?\d*,? ?)+\)',
               r'\{', r'\}', ':'],
}


def build_pdf(path: pathlib.Path, jobname: str = None, sol: bool = False,
              rub: bool = False, clean: bool = True,
              quiet: bool = True) -> pathlib.Path:
    """Run pdflatex on one document.

    Args:
        path: the .tex file, suffix optional
        jobname: output basename, defaults to the input's
        sol: define \\sol, revealing the answers
        rub: define \\rub, revealing the rubric (needs sol too)
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
        command += ['\\def\\sol{1} \\def\\rub{1} \\input{' + path.name + '}']
    elif sol:
        command += ['\\def\\sol{1} \\input{' + path.name + '}']
    else:
        command += [path.name]

    subprocess.run(command, check=True, cwd=path.parent,
                   capture_output=quiet, text=True)

    if clean:
        clean_up(path)

    return path.parent / f'{jobname or path.name}.pdf'


def find_config(path: pathlib.Path) -> dict:
    """Read the solrub.toml governing a document.

    Walks up from the document's folder to the filesystem root and takes
    the first file found, so one solrub.toml at a problem repo's root
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


def sum_points(path: pathlib.Path) -> None:
    """Print the point total of a document.

    Reads the [points] table of the repo's solrub.toml, which names the
    regexes that find a count; POINTS_DEFAULT fills in whatever it omits.
    A repo writing [20 points] rather than [20 pts] must say so, or the
    count silently skips those problems.

    Raises:
        SystemExit: the optional sum-pts dependency is not installed
    """
    if importlib.util.find_spec('sum_pts') is None:
        sys.exit('summing points needs sum-pts: pip install "solrub[pts]"')

    points = {**POINTS_DEFAULT, **find_config(path).get('points', {})}

    command = [
        sys.executable, '-m', 'sum_pts', f"{path}",
        '--left', points['left'], '--right', points['right'],
        '--points', points['points'], '--prefix', points['prefix'],
    ]
    for pattern in points['remove']:
        command += ['-r', pattern]

    subprocess.run(command, check=True)


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
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the pdflatex transcript')
    parser.add_argument('-V', '--version', action='version',
                        version=f'%(prog)s {__version__}')
    parser.add_argument('path', nargs='+',
                        help='.tex files, globs or directories to build')

    args = parser.parse_args()

    try:
        paths = resolve(args.path)
    except FileNotFoundError as error:
        sys.exit(str(error))
    if not paths:
        sys.exit('nothing to build: every match was a fragment or a build')

    failed = []
    for path in paths:
        print(f'==> {path}', flush=True)

        # One unbuildable document must not strand the rest of the batch,
        # so collect the failures and report them together at the end.
        try:
            built = [build_pdf(path, quiet=not args.verbose)]

            if args.sol:
                built.append(build_pdf(path, jobname=f'{path.stem}_sol',
                                       sol=True, quiet=not args.verbose))

            if args.rub:
                built.append(build_pdf(path, jobname=f'{path.stem}_rub',
                                       sol=True, rub=True,
                                       quiet=not args.verbose))

            print('    ' + '  '.join(pdf.name for pdf in built), flush=True)
        except subprocess.CalledProcessError as error:
            failed.append(path)
            if error.stdout:
                print(latex_error(error.stdout), file=sys.stderr, flush=True)

        # Counting points only reads the source, so it is still worth
        # doing for a document pdflatex could not build.
        if args.pts:
            try:
                sum_points(path)
            except subprocess.CalledProcessError:
                print(f'could not count points in {path}', file=sys.stderr)

    if failed:
        names = ', '.join(str(path) for path in failed)
        sys.exit(f'failed: {names}\nthe .log beside each holds the error')


if __name__ == "__main__":
    main()
