"""Build assignments from a repo of LaTeX problems.

A problem repo keeps each problem in its own .tex fragment under
problems/, with its solution and rubric alongside the question, and an
assignment is a short document that inputs the ones it wants.  Problems
outlive the assignment they were written for; this package is the tooling
that makes that layout worth the trouble.

Four jobs, one per module:

    build     one document to three PDFs, student / solution / rubric
    points    the point total per problem, via sum-pts
    library   every problem to a browsable PDF, one per topic folder
    usage     which problems each assignment used, and which none did

config holds the lookups they share, all of them a walk up the folder
tree, and example writes a working repo to copy the layout from.  See
README.md for the command line and docs/points.md for the point config.
"""

from ._version import __version__
from .build import build_pdf, is_document, resolve, uses_macro
from .cli import main
from .config import find_config, find_repo
from .example import scaffold
from .library import browse
from .points import sum_points
from .usage import usage

__all__ = ['browse', 'build_pdf', 'find_config', 'find_repo', 'is_document',
           'main', 'resolve', 'scaffold', 'sum_points', 'usage',
           'uses_macro', '__version__']
