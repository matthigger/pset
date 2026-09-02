#!/usr/bin/env python3
"""Build the student, solution and rubric PDFs of a LaTeX assignment.

One .tex source carries all three copies.  The \\sol and \\rub macros mark
what only the answer key and the rubric show, \\stud what only the student
copy shows, and each build is a pdflatex run defining \\showsol, \\showrub
or neither.  The flags are deliberately not named \\sol and \\rub: a
document cannot both define a macro and test whether it is defined, and
the collision would silently leak answers onto the student copy.  All
three copies are built unless --no-sol or --no-rub says otherwise.

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

# The LaTeX \prob{[20 pts (8, 12)]: title} convention, which is all these
# defaults describe.  Notably absent is 'points': sum-pts already matches
# both "20 pts" and "20 points", and pinning it narrower is how a repo
# silently undercounts itself.  Keys are sum-pts' own parameter names, so
# a [points] table in solrub.toml reaches every knob it has.
POINTS_DEFAULT = {
    'left': r'\[',
    'right': r'\]',
    'prefix': r' *\\prob',
    'rm_list': [r'\(\d+.?\d* each\)', r'\((\d+.?\d*,? ?)+\)',
                r'\{', r'\}', ':'],
}

POINTS_HELP = ('https://github.com/matthigger/solrub'
               '/blob/main/docs/points.md')


class PointsError(Exception):
    """The point-counting patterns did not fit the document."""


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
    """Print the point total of a document, per problem.

    The [points] table of the repo's solrub.toml is handed straight to
    sum-pts, so its parameter names are the keys and its own defaults
    cover anything both that table and POINTS_DEFAULT leave out.  Calling
    sum-pts here rather than as a subprocess is what makes pt_split
    reachable, since its command line never exposed that one.

    Raises:
        SystemExit: sum-pts is not installed
        PointsError: the patterns matched nothing, or sum-pts choked on
            them.  Any exception counts: a pattern that does not fit
            surfaces as a regex error, a missing digit or a duplicate
            problem name depending on where it first goes wrong, and the
            reader needs the same advice for all of them.
    """
    try:
        import sum_pts
    except ModuleNotFoundError:
        sys.exit('summing points needs sum-pts: pip install "solrub[pts]"')

    points = {**POINTS_DEFAULT, **find_config(path).get('points', {})}

    counter = sum_pts.PointCounter()
    try:
        counter.parse_file(file=path, **points)
    except Exception as error:
        raise PointsError(
            f'{type(error).__name__}: {error}\n'
            f'the [points] patterns do not fit {path}, see {POINTS_HELP}')

    if counter.df.empty:
        raise PointsError(
            f'found no points in {path}\n'
            f'the [points] patterns do not fit it, see {POINTS_HELP}')

    print(counter.to_df().to_markdown())


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
            except PointsError as error:
                print(error, file=sys.stderr, flush=True)

    if failed:
        names = ', '.join(str(path) for path in failed)
        sys.exit(f'failed: {names}\nthe .log beside each holds the error')


if __name__ == "__main__":
    main()
