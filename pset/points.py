"""Sum the points per problem of a document, via sum-pts.

How a point count is written varies by repo, so the regexes come from the
[points] table of the repo's pset.toml (see docs/points.md).  The defaults
below describe the one convention worth assuming.
"""

import pathlib
import sys
import warnings

from .config import find_config

# The LaTeX \prob{[20 pts (8, 12)]: title} convention, which is all these
# defaults describe.  Notably absent is 'points': sum-pts already matches
# both "20 pts" and "20 points", and pinning it narrower is how a repo
# silently undercounts itself.  Keys are sum-pts' own parameter names, so
# a [points] table in pset.toml reaches every knob it has.
POINTS_DEFAULT = {
    'left': r'\[',
    'right': r'\]',
    'prefix': r' *\\prob',
    'rm_list': [r'\(\d+.?\d* each\)', r'\((\d+.?\d*,? ?)+\)',
                r'\{', r'\}', ':'],
}

POINTS_HELP = ('https://github.com/matthigger/pset'
               '/blob/main/docs/points.md')


class PointsError(Exception):
    """The point-counting patterns did not fit the document."""


def sum_points(path: pathlib.Path) -> None:
    """Print the point total of a document, per problem.

    The [points] table of the repo's pset.toml is handed straight to
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
    # sum-pts 0.0.4 writes its regex defaults as plain strings, so
    # compiling it warns three times about invalid escapes.  That is its
    # to fix, but the noise would land in output this tool promises to
    # keep quiet, and it only appears until the .pyc is cached.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', SyntaxWarning)
            import sum_pts
    except ModuleNotFoundError:
        sys.exit('summing points needs sum-pts: pip install "pset[pts]"')

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

    # to_df fills its empty cells with '' on a float column, which pandas
    # warns about.  Same story as the SyntaxWarning above: not ours to
    # fix, and it would land in the middle of the table being printed.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', FutureWarning)
        table = counter.to_df()

    print(table.to_markdown())
