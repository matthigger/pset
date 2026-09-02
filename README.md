# solrub

Build the student, solution and rubric PDFs of a LaTeX assignment.

One `.tex` source carries all three copies.  `\sol` marks what only the
answer key shows and `\rub` what only the grading rubric shows; each copy is
a `pdflatex` run defining a different subset of them.

```bash
pip install solrub
```

## Use

```bash
solrub quiz1a              # quiz1a.pdf, quiz1a_sol.pdf, quiz1a_rub.pdf
solrub quiz1*              # every version at once
solrub quiz1/              # every document in a folder
solrub --no-sol --no-rub blank
```

All three copies are the default; `--no-sol` and `--no-rub` opt out.

Arguments are files, globs or directories, with the `.tex` suffix optional.
Globs are expanded by the tool rather than left to the shell, so `quiz1*`
works the same on Windows.  Two filters keep a wide pattern honest: sibling
builds (`quiz1a.pdf`, `quiz1a_sol.pdf`) collapse onto the `.tex` they came
from, and a fragment with no `\documentclass` is skipped.

The pdflatex transcript is hidden, leaving one line per document:

    ==> quiz1a.tex
        quiz1a.pdf  quiz1a_sol.pdf  quiz1a_rub.pdf

A failure prints the error pdflatex reported and keeps that document's
`.log`, but does not stop the rest of the batch; the failures are listed at
the end and the exit status is non-zero.  `-v` restores the full transcript.

## Counting points

`-p` sums the points per problem, using
[sum-pts](https://pypi.org/project/sum-pts/): `pip install "solrub[pts]"`.

How a count is written varies by repo, so the patterns live beside the
documents rather than in this tool.  Drop a `solrub.toml` at the root of a
problem repo and it governs every assignment under it:

```toml
# problems read:  \prob{[20 pts (8, 12)]: Bayes Net}
[points]
left = '\['
right = '\]'
prefix = ' *\\prob'
points = 'pts?'
remove = ['\(\d+.?\d* each\)', '\((\d+.?\d*,? ?)+\)', '\{', '\}', ':']
```

Anything omitted keeps its default, so a repo writing `[20 points]` rather
than `[20 pts]` needs only:

```toml
[points]
points = 'points'
```

That one is worth stating explicitly: the default `pts?` does not match
`points`, and rather than failing it matches the `pts` inside a
`(4 pts each)` split, silently returning a total that is too low.

Points are counted from the source, so `-p` still reports on a document
that failed to build.

## In the document

Three macros divide the source.  `\answer` and `\rubric` are hidden by
default and revealed by their build; `\exam` is the reverse, student-only
content such as the blank space left for the work, dropped from both keys.

```latex
\newcommand{\answer}[1]{}
\newcommand{\rubric}[1]{}
\newcommand{\exam}[1]{#1}

\ifdefined\sol
  \renewcommand{\answer}[1]{#1}
  \renewcommand{\exam}[1]{}
\fi

\ifdefined\rub
  \renewcommand{\rubric}[1]{#1}
  \renewcommand{\exam}[1]{}
\fi
```

## Requires

`pdflatex` on the PATH, and Python 3.9 or newer.
