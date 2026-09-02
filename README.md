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

All three copies are the default; `--no-sol` and `--no-rub` opt out.  Add
`-p` to sum the points (needs `pip install "solrub[pts]"`).

Arguments are files, globs or directories, with the `.tex` suffix optional.
Globs are expanded by the tool rather than left to the shell, so `quiz1*`
works the same on Windows.  Two filters keep a wide pattern honest: sibling
builds (`quiz1a.pdf`, `quiz1a_sol.pdf`) collapse onto the `.tex` they came
from, and a fragment with no `\documentclass` is skipped.  A failed document
does not stop the rest of the batch; the failures are listed at the end.

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
