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
```

All three copies are the default, minus any that would come out empty: a
document with no `\rub` anywhere in it gets no rubric copy, since that copy
would only duplicate the answer key.  It says so when it skips one.

    ==> exam1a.tex
        exam1a.pdf  exam1a_sol.pdf
        no \rub in it, rub copy skipped

The check follows `\input` through the whole tree, because the content
macros usually sit in the problem files rather than the document.  Where the
tree cannot be read to the end — a missing file, or an `\input` whose path
is built from a macro — it builds the copy rather than guess.  `--rub` forces
one, `--no-rub` refuses it outright, and the same pair exists for `--sol`.

If your repo calls the macros something else, name them in `solrub.toml`:

```toml
[macros]
sol = 'answer'
rub = 'rubric'
```

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
[sum-pts](https://github.com/matthigger/sum_pts): `pip install "solrub[pts]"`.

```
solrub -p quiz1a
```

The default expects a bracket at the front of a `\prob{...}` title, and
reads both spellings:

```latex
\prob{[20 pts (8, 12)]: Bayes Net}
\prob{[16 points (4 pts each)]: Ecology System}
```

If that is not your convention, a `[points]` table in a `solrub.toml` at your
repo root overrides it for every document underneath.  The keys are sum-pts'
own parameters, so its documentation is the reference:

```toml
[points]
prefix = ' *\\question'
points = '(marks|pts?)'
```

When the patterns do not fit, solrub says so and links to
[docs/points.md](docs/points.md), which explains each key and the traps.
Points are read from the source, so `-p` still reports on a document that
failed to build.

## In the document

Three macros divide the source.  `\sol` and `\rub` are hidden by default and
revealed by their own build; `\stud` is the reverse, student-only content
such as the blank space left for the work, dropped from both keys.

```latex
\newcommand{\sol}[1]{}
\newcommand{\rub}[1]{}
\newcommand{\stud}[1]{#1}

\ifdefined\showsol
  \renewcommand{\sol}[1]{#1}
  \renewcommand{\stud}[1]{}
\fi

\ifdefined\showrub
  \renewcommand{\rub}[1]{#1}
  \renewcommand{\stud}[1]{}
\fi
```

```latex
\stud{\vfill}
\sol{The boundary is $x = 3$.}
\rub{6 pts: correct slope.  3 pts if the intercept is off.}
```

The flags solrub defines are `\showsol` and `\showrub`, deliberately not
`\sol` and `\rub`.  A document cannot both define a macro and ask whether
it is defined: `\newcommand{\sol}` would make `\ifdefined\sol` true on
every build, so the student copy would silently print the answers.

## Requires

`pdflatex` on the PATH, and Python 3.9 or newer.
