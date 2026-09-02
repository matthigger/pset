"""Render the whole problem library, one PDF per topic folder.

A problem is a .tex fragment with no \\documentclass of its own, so it
cannot be built directly.  This wraps every problem in one topic folder of
problems/ into a generated document and builds that, giving one browsable
PDF per topic in problems_pdf/.  Two uses: reading what problems already
exist before writing another, and catching the one that stopped compiling.

The generated document is written into problems_pdf/, one level under the
repo root, because a problem's own \\includegraphics paths are written
relative to an assignment folder at that same depth (../problems/x.png).
Building anywhere else silently loses every figure.
"""

import pathlib
from datetime import datetime
from importlib.resources import files
from typing import Optional

from .build import build_pdf
from .config import BUILD, PROBLEMS

# A repo dropping this at its root gets its own layout for the generated
# document; otherwise the copy shipped in the package is used.
TEMPLATE_NAME = 'pset_browse.tex'

# Root-level fragments inputted into the generated document if the repo
# has them, in this order: the packages have to load before the commands
# that configure them.  A repo naming them otherwise overrides the whole
# template instead.
PREAMBLE_INPUT = ['packages.tex', 'command.tex']

# Problem files skipped: a template is a starting point to copy, not a
# problem, and it usually does not compile on its own.
SKIP = '*template*.tex'


def read_template(root: pathlib.Path) -> str:
    """Read the document template --browse wraps a topic's problems in.

    Returns:
        template: the repo's own pset_browse.tex, else the packaged
            default.  Carries the HW_TITLE, DATE_BUILD, PREAMBLE and
            PROBLEMS placeholders that render_topic fills in.
    """
    local = root / TEMPLATE_NAME
    if local.is_file():
        return local.read_text()
    return (files('pset') / 'data' / TEMPLATE_NAME).read_text()


def problem_tex(path: pathlib.Path, root: pathlib.Path) -> str:
    """Give the LaTeX that titles and inputs one problem.

    Args:
        path: the problem's .tex file
        root: the repo root, which the printed title is relative to

    Returns:
        tex: a \\prob title naming the problem, then its \\input.  The
            path is relative to problems_pdf/ rather than absolute, so
            the generated document reads like a hand-written assignment.
    """
    title = path.relative_to(root / PROBLEMS).as_posix()

    # An underscore is a math subscript to LaTeX, so a title carrying one
    # has to escape it.  The \input path does not: that argument is
    # scanned as a filename, not typeset.
    title = title.replace('_', r'\_')
    target = pathlib.Path('..') / path.relative_to(root)
    return f'\n\n\\prob{{{title}}}\n\\input{{{target.as_posix()}}}'


def render_topic(paths: list[pathlib.Path], out: pathlib.Path,
                 root: pathlib.Path, title: str, rub: bool = False,
                 quiet: bool = True) -> pathlib.Path:
    """Build one PDF holding every problem given.

    Args:
        paths: the problem .tex files, in the order to print them
        out: the PDF to write, inside problems_pdf/
        root: the repo root
        title: printed at the top, normally the topic folder's name
        rub: show the rubric boxes as well as the solutions
        quiet: swallow the pdflatex transcript

    Returns:
        pdf: the file written

    Raises:
        subprocess.CalledProcessError: pdflatex rejected the document
    """
    preamble = '\n'.join(f'\\input{{../{name}}}' for name in PREAMBLE_INPUT
                         if (root / name).is_file())
    problems = ''.join(problem_tex(path, root) for path in paths)

    template = read_template(root)
    template = template.replace('HW_TITLE', title.replace('_', r'\_'))
    template = template.replace('DATE_BUILD',
                                datetime.today().strftime('%Y-%b-%d %H:%M'))
    template = template.replace('PREAMBLE', preamble)
    template = template.replace('PROBLEMS', problems)

    tex = out.with_suffix('.tex')
    tex.parent.mkdir(parents=True, exist_ok=True)
    tex.write_text(template)

    try:
        # Solutions always: browsing the library is an author's job, and a
        # problem whose solution stopped compiling is one worth catching.
        # The jobname is passed rather than left to pdflatex, which would
        # otherwise take it from the \input it is handed.
        return build_pdf(tex, jobname=tex.stem, sol=True, rub=rub,
                         quiet=quiet)
    finally:
        # The generated source is derived, so leaving it beside the PDF
        # only invites someone to edit the copy that gets overwritten.
        # Dropped on a failure too; the .log holds what went wrong.
        tex.unlink(missing_ok=True)


def topics(root: pathlib.Path) -> dict:
    """Group a repo's problems by the topic folder they sit in.

    Args:
        root: the repo root

    Returns:
        found: {topic_name: [problem paths, sorted]}, one key per folder
            directly under problems/ that holds any problem, nested
            subfolders included in their top-level topic.  Insertion
            order is alphabetical by topic.
    """
    found = {}
    for folder in sorted((root / PROBLEMS).iterdir()):
        if not folder.is_dir():
            continue
        paths = sorted(set(folder.glob('**/*.tex'))
                       - set(folder.glob(f'**/{SKIP}')))
        if paths:
            found[folder.name] = paths
    return found


def browse(root: Optional[pathlib.Path] = None, rub: bool = False,
           quiet: bool = True) -> list[pathlib.Path]:
    """Render every topic of a repo's problem library to its own PDF.

    Args:
        root: the repo root
        rub: show the rubric boxes as well as the solutions
        quiet: swallow the pdflatex transcript

    Returns:
        failed: the topics pdflatex rejected.  One bad problem must not
            strand the rest of the library, so the failures are collected
            rather than raised, and the caller reports them together.
    """
    found = topics(root)
    if not found:
        print(f'no problems under {root / PROBLEMS}')
        return []

    failed = []
    for topic, paths in found.items():
        print(f'==> {topic} ({len(paths)} problems)', flush=True)
        out = root / BUILD / topic
        try:
            pdf = render_topic(paths, out=out, root=root, title=topic,
                               rub=rub, quiet=quiet)
            print(f'    {pdf.relative_to(root).as_posix()}', flush=True)
        except Exception as error:
            failed.append(out.with_suffix('.tex'))
            print(f'    failed: {error}', flush=True)
    return failed
