"""Command line interface.

Four jobs behind one command.  Named documents are built (the default);
--browse and --usage act on the whole repo and take no documents;
--example writes a new one.  The repo-wide modes find the repo root by
walking up from the working folder, so they run from anywhere inside it.
"""

import argparse
import pathlib
import subprocess
import sys

from ._version import __version__
from .build import (MACROS_DEFAULT, build_pdf, latex_error, resolve,
                    uses_macro)
from .config import README, RepoError, find_config, find_repo
from .example import scaffold, write_readme
from .library import browse
from .points import PointsError, sum_points
from .usage import usage


def parse_args(argv=None) -> argparse.Namespace:
    """Define and read the command line."""
    parser = argparse.ArgumentParser(
        prog='pset',
        description='Build assignments from a repo of LaTeX problems, '
                    'each carrying its own solution and rubric.')

    parser.add_argument('-s', '--sol', action=argparse.BooleanOptionalAction,
                        default=None,
                        help='build solution copy, or --no-sol never.  '
                             'Left alone it builds unless the document '
                             'has no \\sol content')
    parser.add_argument('-r', '--rub', action=argparse.BooleanOptionalAction,
                        default=None,
                        help='build rubric copy, or --no-rub never.  '
                             'Left alone it builds unless the document '
                             'has no \\rub content')
    parser.add_argument('-p', '--pts', action='store_true', help='sum points')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='show the pdflatex transcript')
    parser.add_argument('-V', '--version', action='version',
                        version=f'%(prog)s {__version__}')

    repo = parser.add_argument_group(
        'whole repo', 'act on the problem repo around the working folder')
    repo.add_argument('--browse', action='store_true',
                      help='render every problem to problems_pdf/, one PDF '
                           'per topic folder')
    repo.add_argument('--usage', action='store_true',
                      help='write prob_file_pair.json: which problems each '
                           'assignment uses, and the reverse')
    repo.add_argument('-o', '--out', default=None,
                      help='where --usage writes')
    repo.add_argument('--example', nargs='?', const='', metavar='DIR',
                      help='write an example problem repo to DIR '
                           '(default pset_example/) and stop')
    repo.add_argument('--readme', action='store_true',
                      help=f'write {README} beside the problems folder')

    parser.add_argument('path', nargs='*',
                        help='.tex files, globs or directories to build')

    return parser.parse_args(argv)


def build_one(path: pathlib.Path, args: argparse.Namespace) -> bool:
    """Build the copies of one document, reporting each as it lands.

    Args:
        path: the .tex file
        args: the parsed command line

    Returns:
        ok: False where pdflatex rejected the document.  Returned rather
            than raised so one unbuildable document does not strand the
            rest of the batch.
    """
    macros = {**MACROS_DEFAULT, **find_config(path).get('macros', {})}
    skipped = []
    ok = True
    try:
        built = [build_pdf(path, quiet=not args.verbose)]

        for kind, asked in (('sol', args.sol), ('rub', args.rub)):
            if asked is False:
                continue
            # Asked for outright, build it; left to us, skip the copy a
            # document with none of that content would duplicate.
            if asked is None and uses_macro(path, macros[kind]) is False:
                skipped.append(kind)
                continue
            built.append(build_pdf(path, jobname=f'{path.stem}_{kind}',
                                   sol=True, rub=kind == 'rub',
                                   quiet=not args.verbose))

        print('    ' + '  '.join(pdf.name for pdf in built), flush=True)
        for kind in skipped:
            print(f'    no \\{macros[kind]} in it, {kind} copy skipped',
                  flush=True)
    except subprocess.CalledProcessError as error:
        ok = False
        if error.stdout:
            print(latex_error(error.stdout), file=sys.stderr, flush=True)

    # Counting points only reads the source, so it is still worth doing
    # for a document pdflatex could not build.
    if args.pts:
        try:
            sum_points(path)
        except PointsError as error:
            print(error, file=sys.stderr, flush=True)

    return ok


def run_repo(args: argparse.Namespace) -> int:
    """Run the modes that act on the whole repo.

    Returns:
        status: the process exit status
    """
    try:
        root = find_repo()
    except RepoError as error:
        print(error, file=sys.stderr)
        return 1

    failed = []
    if args.readme:
        written = write_readme(root)
        print(f'wrote {written}' if written
              else f'{root / README} exists already, left alone')
    if args.browse:
        failed = browse(root, rub=bool(args.rub), quiet=not args.verbose)
    if args.usage:
        usage(root, out=pathlib.Path(args.out) if args.out else None)

    if failed:
        names = ', '.join(path.stem for path in failed)
        print(f'failed: {names}\nrerun with -v for the pdflatex transcript',
              file=sys.stderr)
        return 1
    return 0


def main(argv=None) -> None:
    """Run the command line interface.

    Raises:
        SystemExit: always, carrying the exit status
    """
    args = parse_args(argv)

    if args.example is not None:
        try:
            scaffold(args.example or None, readme=args.readme or None)
        except FileExistsError as error:
            sys.exit(str(error))
        sys.exit(0)

    if args.browse or args.usage or args.readme:
        if args.path:
            sys.exit('--browse, --usage and --readme act on the whole repo '
                     'and take no documents')
        sys.exit(run_repo(args))

    if not args.path:
        sys.exit('nothing to build: name a document, or see pset --help '
                 'for the whole-repo modes')

    try:
        paths = resolve(args.path)
    except FileNotFoundError as error:
        sys.exit(str(error))
    if not paths:
        sys.exit('nothing to build: every match was a fragment or a build')

    failed = []
    for path in paths:
        print(f'==> {path}', flush=True)
        if not build_one(path, args):
            failed.append(path)

    if failed:
        names = ', '.join(str(path) for path in failed)
        sys.exit(f'failed: {names}\nthe .log beside each holds the error')
