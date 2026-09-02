# pset

Build assignments from a repo of LaTeX problems, each carrying its own
solution and rubric.

A problem is worth more than the assignment it was written for.  Keep each
one in its own `.tex` file with its solution and rubric beside the
question, and an assignment becomes a short document that `\input`s the
ones it wants: reusable across terms, reviewable in version control, and
buildable into a student copy, an answer key and a grading rubric from the
one source.

```bash
pip install pset
pset --example        # a working repo to copy the layout from
```

## The layout

```
problems/                  every problem, grouped by topic
    number_rep/
        base_convert01.tex
        2s_comp_overflow01.tex
    logic/
        boolean_simplify01.tex
pset.tex                   \prob, \sol, \rub, \stud (generated)
packages.tex               shared by every assignment
command.tex                your styling, inputs pset.tex
hw1/
    hw1.tex                metadata, then the problems it inputs
```

`pset --example` writes exactly that, five problems and an assignment that
builds, so the fastest way to read the rest of this is to build it:

```bash
pset --example
cd pset_example/hw_example
pset hw_example
```

## Building an assignment

```bash
pset quiz1a              # quiz1a.pdf, quiz1a_sol.pdf, quiz1a_rub.pdf
pset quiz1*              # every version at once
pset quiz1/              # every document in a folder
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

## In the document

Three macros divide the source, and each copy is the same document with a
different subset of them switched on.

| macro | student | `_sol` | `_rub` | what goes in it |
|-------|---------|--------|--------|-----------------|
| plain text | yes | yes | yes | the question |
| `\stud` | yes | | | space for the work |
| `\sol` | | yes | yes | the answer |
| `\rub` | | | yes | how to mark it |

`\sol` and `\rub` are hidden by default and revealed by their own build.
`\stud` is the reverse: on by default and dropped from both keys.

You do not write those definitions.  `pset --init` generates them into a
`pset.tex` at your repo root, and each document inputs it beside whatever
other shared preamble it already has:

```latex
\input{../pset.tex}
```

The path is relative to the document being built, not to the file holding
the line, so putting it in a `command.tex` that every document already
inputs wires up the whole repo at once.  `--init` prints the line rather
than editing your documents, and re-running it upgrades the file in place
(it refuses to touch a `pset.tex` it did not write).

Generating it is not just convenience.  Hand-rolled, the definitions are
easy to get subtly wrong, and the failure mode is a student PDF with the
answers in it.

```latex
Find the decision boundary.

\stud{\vfill}
\sol{The boundary is $x = 3$.}
\rub{6 pts: correct slope.  3 pts if the intercept is off.}
```

`\stud` exists because the student copy and the answer key want opposite
things in the same spot.  The student needs room to work, so a problem ends
with `\stud{\vfill}` or `\stud{\vspace{2in}}`; the key wants that space
gone, or every answer sits alone on its own page and the grader pages
through five sheets to mark one problem.  Anything else addressed only to
the student belongs in it too: `\stud{Show your work.}`, a fill-in table,
a tear-off answer sheet.

Note it wraps content rather than switching a mode, so it takes an argument
like the other two: `\stud{...}`, not `\begin{stud}`.  Nesting works, so
`\sol{... \rub{...}}` puts a per-part rubric inside the answer.

## Styling them

`pset.tex` carries the mechanism, which is pset's, and leaves the look to
you through three hooks.  They default to printing their argument plainly,
so the generated file needs no packages at all and cannot collide with
your package set.  Redefine any of them after the `\input`:

```latex
\renewcommand{\solstyle}[1]{
  \begin{tcolorbox}[colback=blue!3!white,title=Solution,breakable]#1\end{tcolorbox}}

\renewcommand{\rubstyle}[1]{
  \begin{tcolorbox}[colback=green!3!white,title=Rubric,breakable]#1\end{tcolorbox}}

\renewcommand{\probstyle}[2]{\section*{Problem #1 #2}}
```

`\probstyle` takes the number and the title separately.  `\prob` itself is
mechanism, not taste: `-p` reads the points out of `\prob{[20 pts]: title}`,
so the macro name is part of the contract even though its look is yours.

The flags pset defines are `\showsol` and `\showrub`, deliberately not
`\sol` and `\rub`.  A document cannot both define a macro and ask whether
it is defined: `\newcommand{\sol}` would make `\ifdefined\sol` true on
every build, so the student copy would silently print the answers.

If your repo calls the macros something else, name them in `pset.toml`:

```toml
[macros]
sol = 'answer'
rub = 'rubric'
```

## Reading the library

```bash
pset --browse
```

renders every problem into `problems_pdf/`, one PDF per topic folder of
`problems/`, with the solutions shown.  Worth doing before writing a new
problem, and it catches the one that has stopped compiling.  A topic that
fails does not stop the others; the failures are listed at the end.

The generated document comes from a template which inputs your repo's
`packages.tex` and `command.tex`.  Drop your own `pset_browse.tex` at the
repo root to change the layout.

## Which problems have I already used?

```bash
pset --usage
```

writes `prob_file_pair.json`, pairing each problem with the assignments
that `\input` it and each assignment with its problems.  It flags any
problem used by more than one assignment, which is how the same question
lands on both the homework and the exam, and counts the ones never used
(they keep an empty list, so `grep '\[\]'` finds them).  `-o` writes
elsewhere, which is how a per-term snapshot gets kept.

`--browse` and `--usage` both act on the whole repo and find its root by
walking up from the working folder, so they run from anywhere inside it.
The root is the folder holding `problems/`.

## Counting points

`-p` sums the points per problem, using
[sum-pts](https://github.com/matthigger/sum_pts): `pip install "pset[pts]"`.

```
pset -p quiz1a
```

The default expects a bracket at the front of a `\prob{...}` title, and
reads both spellings:

```latex
\prob{[20 pts (8, 12)]: Bayes Net}
\prob{[16 points (4 pts each)]: Ecology System}
```

If that is not your convention, a `[points]` table in a `pset.toml` at your
repo root overrides it for every document underneath.  The keys are sum-pts'
own parameters, so its documentation is the reference:

```toml
[points]
prefix = ' *\\question'
points = '(marks|pts?)'
```

When the patterns do not fit, pset says so and links to
[docs/points.md](docs/points.md), which explains each key and the traps.
Points are read from the source, so `-p` still reports on a document that
failed to build.

## Setting up a repo

```bash
pset --init            # write pset.tex, print the line that inputs it
pset --readme          # write README_pset.md beside problems/
pset --example         # or scaffold a whole working repo from scratch
```

`--init` is the one an existing repo needs; it writes `pset.tex` and
nothing else, since a repo with assignments in it already has a layout and
a preamble, and neither is pset's to rewrite.  `--readme` adds a short
guide to the layout and commands for whoever clones the repo next;
`--example` offers one too, and remembers the answer in
`~/.config/pset/pset.toml` so it only asks once.

## Requires

`pdflatex` on the PATH, and Python 3.9 or newer.
