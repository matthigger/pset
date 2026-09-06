# pset

Build assignments from a repo of LaTeX problems, each carrying its own
solution and rubric.

- every problem is its own `.tex` file, with the question, the solution and
  the rubric together
- an assignment is a short file that `\input`s the problems it wants
- one build gives three PDFs from that one source: the student copy, the
  answer key and the grading rubric
- so problems outlive the assignment they were written for: reusable across
  terms, reviewable in version control, searchable before you write the
  next one

## Installation

```bash
pip install pset
```

Needs `pdflatex` on the PATH and python 3.9 or newer.

## Quick start

`pset --example` writes a small repo that builds: five problems, one
assignment, and the shared preamble around them.

```bash
pset --example
cd pset_example/hw_example
pset hw_example
```

```
==> hw_example.tex
    hw_example.pdf  hw_example_sol.pdf  hw_example_rub.pdf
```

`hw_example.pdf` goes to the students, `hw_example_sol.pdf` is the answer
key, `hw_example_rub.pdf` adds the grading rubric for the TAs.  Opening the
three side by side is the fastest way to read the rest of this.

## The layout

```
pset_example/
    pset.tex              \prob, \sol, \rub, \stud (generated, don't edit)
    packages.tex          the \usepackage lines, shared by every assignment
    command.tex           your styling; inputs pset.tex
    problems/             every problem, grouped by topic
        number_rep/
            base_convert_dec_hex01.tex
            2s_comp_overflow01.tex
            mod_arithmetic01.tex
        logic/
            boolean_simplify01.tex
            cnf_dnf_warmup01.tex
    hw_example/
        hw_example.tex    metadata, then the problems it inputs
```

Each assignment gets its own folder one level under the root, so
`../problems/...` resolves the same way from all of them.

## An assignment

[`hw_example/hw_example.tex`](pset/data/example/hw_example/hw_example.tex),
trimmed to three problems:

```latex
\documentclass[11pt]{article}

\newcommand{\hwtitle}{HW1: Number Representation \& Logic}
\newcommand{\hwdatedue}{Sept 22, 2025 @ 11:59pm}
\newcommand{\course}{Example Course}

\input{../packages.tex}
\input{../command.tex}

\begin{document}
    \input{../header_box.tex}
    \input{../instructions.tex}

    \prob{[24 pts: (6 each)]: Base conversions}
    \input{../problems/number_rep/base_convert_dec_hex01.tex}

    \prob{[23 pts: (14, 9)]: 2's Complement \& Overflow}
    \input{../problems/number_rep/2s_comp_overflow01.tex}

    \prob{[12 pts]: Simplifying a set expression}
    \input{../problems/logic/boolean_simplify01.tex}

\end{document}
```

The assignment holds the metadata, the ordering and the points; every
question is in a problem file.  Reordering it, or swapping in next term's
variant, is a couple of lines.

`\prob{...}` numbers the problem and prints its title.  `pset -p` reads the
points out of the leading bracket, so `[24 pts: (6 each)]` is a convention
worth keeping (see [counting points](#counting-points)).

## A problem

[`problems/logic/boolean_simplify01.tex`](pset/data/example/problems/logic/boolean_simplify01.tex)
in full:

```latex
Simplify the expression below.
Your simplified expression should have the least possible number of set
operators ($\cup$, $\cap$, $^c$).
Show each step by applying and labelling the identity used.

\begin{equation*}
	(A \cap (A \cup B^c))^c
\end{equation*}

\stud{\vfill}

\sol{
	\begin{align*}
		(A \cap (A \cup B^c))^c
		 & = (A^c \cup (A \cup B^c)^c) \quad \text{(De Morgan's Law)}    \\
		 & = (A^c \cup (A^c \cap B^{cc})) \quad \text{(De Morgan's Law)} \\
		 & = (A^c \cup (A^c \cap B)) \quad \text{(Double Negation)}      \\
		 & = A^c \quad \text{(Absorption)}
	\end{align*}
}

\rub{
	\begin{itemize}
		\item 8 pts final expression of $A^c$
		\item 4 pts every step labelled with the identity used
	\end{itemize}
}
```

No `\documentclass` and no `\begin{document}`: the assignment supplies
both.  Three macros divide the content, and each PDF is this same file with
a different subset of them switched on.

| macro | student | `_sol` | `_rub` | what goes in it |
|-------|---------|--------|--------|-----------------|
| plain text | yes | yes | yes | the question |
| `\stud` | yes | | | space for the work |
| `\sol` | | yes | yes | the answer |
| `\rub` | | | yes | how to mark it |

`\sol` and `\rub` are hidden by default and revealed by their own build.
`\stud` runs the other way: on by default, dropped from both keys.  Mostly
it is the blank space left for the work, `\stud{\vfill}` or
`\stud{\vspace{2in}}`, which the keys do not want: leave it in and every
answer sits alone on its own page, so marking one problem means paging
through five sheets.  Anything else addressed only to the student goes in
it too, such as `\stud{Show your work.}` or a table to fill in.

All three wrap their argument rather than switching a mode, so it is
`\stud{...}`, not `\begin{stud}`.  They nest: `\sol{... \rub{...}}` hangs a
per-part rubric off the answer it belongs to.

You never write those definitions.  `pset.tex` at the repo root holds them
and `pset --init` generates it, which is what
[setting up your own repo](#setting-up-your-own-repo) is about.

## Building

```bash
pset hw_example          # hw_example.pdf, _sol.pdf, _rub.pdf
pset quiz1*              # every version at once
pset quiz1/              # every document in a folder
```

Arguments are files, globs or folders, and the `.tex` suffix is optional.
Globs are expanded by pset rather than left to the shell, so `quiz1*` works
the same on Windows.  Two filters keep a wide pattern honest: a sibling
build (`quiz1a_sol.pdf`) collapses onto the `.tex` it came from, and a
fragment with no `\documentclass` is skipped.

All three copies build by default, minus any that would come out empty:

```
==> exam1a.tex
    exam1a.pdf  exam1a_sol.pdf
    no \rub in it, rub copy skipped
```

A document with no `\rub` anywhere in it gets no rubric copy, since that
copy would only duplicate the answer key.  The check follows `\input`
through the whole tree, because the macros usually sit in the problem files
rather than in the document.  Where the tree cannot be read to the end -- a
missing file, or an `\input` path built from a macro -- it builds the copy
rather than guess.  `--sol` and `--rub` force one; `--no-sol` and
`--no-rub` refuse one outright.

The pdflatex transcript is hidden, leaving one line per document.  A
failure prints the error pdflatex reported and keeps that document's
`.log`, but does not stop the rest of the batch: the failures are listed at
the end and the exit status is non-zero.  `-v` restores the full
transcript.

## Styling

`pset.tex` carries the mechanism, which is pset's, and leaves the look to
you through three hooks.  They default to printing their argument plainly,
so the generated file needs no packages at all and cannot collide with your
package set.  `\renewcommand` any of them after the `\input`, as
[`command.tex`](pset/data/example/command.tex) does:

```latex
\input{../pset.tex}

\renewcommand{\solstyle}[1]{
	\begin{tcolorbox}[colback=blue!3!white,colframe=blue!40!black,title=Solution,breakable]
		#1
	\end{tcolorbox}
}

\renewcommand{\rubstyle}[1]{
	\begin{tcolorbox}[colback=green!3!white,colframe=green!40!black,title=Rubric,breakable]
		#1
	\end{tcolorbox}
}

\renewcommand{\probstyle}[2]{\section*{Problem #1 #2}}
```

`\probstyle` takes the number and the title separately.

Two names are pset's rather than yours.  `\prob` is the macro `-p` reads
points out of, so it is part of the contract even though its look is yours.
And the build flags are `\showsol` and `\showrub`, deliberately not `\sol`
and `\rub`: a document cannot both define a macro and ask whether it is
defined, so `\newcommand{\sol}` would make `\ifdefined\sol` true on every
build and print the answers on the student copy.

If your repo already calls the content macros something else, name them in
a `pset.toml` at the repo root:

```toml
[macros]
sol = 'answer'
rub = 'rubric'
```

## Setting up your own repo

```bash
pset --init
```

is all an existing repo needs.  It writes `pset.tex` and nothing else,
since a repo with assignments in it already has a layout and a preamble,
and neither is pset's to rewrite.  Add the line it prints to each document,
beside whatever shared preamble that document already inputs:

```latex
\input{../pset.tex}
```

The path is relative to the document being built, not to the file holding
the line, so putting it in a `command.tex` that every document already
inputs wires up the whole repo at once.

Re-running `--init` upgrades `pset.tex` in place, and it refuses to touch
one it did not write.  Generating the file is not only convenience:
hand-rolled, those definitions are easy to get subtly wrong, and the
failure mode is a student PDF with the answers in it.

`pset --readme` drops a short guide to the layout and the commands beside
`problems/`, for whoever clones the repo next.  `--example` offers one too,
and remembers the answer in `~/.config/pset/pset.toml` so it asks once.

## Browsing the library

```bash
pset --browse
```

renders every problem into `problems_pdf/`, one PDF per topic folder of
`problems/`, with the solutions shown (`--rub` adds the rubrics).  Worth
doing before writing a new problem, and it catches the one that has stopped
compiling.  A topic that fails does not stop the others; the failures are
listed at the end.

The generated document inputs your repo's `packages.tex` and `command.tex`,
so a problem looks the way it will on an assignment.  Files matching
`*template*.tex` are skipped, and dropping your own `pset_browse.tex` at
the repo root changes the layout.

## Which problems have I already used?

```bash
pset --usage
```

writes `prob_file_pair.json`, pairing each problem with the assignments
that `\input` it and each assignment with its problems:

```json
{
    "file_to_prob": {
        "hw_example/hw_example": [
            "number_rep/base_convert_dec_hex01",
            "logic/boolean_simplify01"
        ]
    },
    "prob_to_file": {
        "logic/boolean_simplify01": ["hw_example/hw_example"],
        "logic/cnf_dnf_warmup01": []
    }
}
```

A problem listed under two assignments is how the same question lands on
both the homework and the exam; pset flags those as it writes.  A problem
never used keeps an empty list, so `grep '\[\]'` finds the unused ones.
`-o` writes elsewhere, which is how a per-term snapshot gets kept.

`--browse` and `--usage` both act on the whole repo and find its root by
walking up from the working folder, so they run from anywhere inside it.
The root is the folder holding `problems/`.

## Counting points

```bash
pip install "pset[pts]"
pset -p hw_example
```

sums the points per problem with
[sum-pts](https://github.com/matthigger/sum_pts):

```
| part                         |    | extra   |   part total |
|:-----------------------------|---:|:--------|-------------:|
| Base conversions             | 24 |         |           24 |
| 2's Complement \& Overflow   | 23 |         |           23 |
| Modular Arithmetic           | 16 | 2.0     |           18 |
| Simplifying a set expression | 12 |         |           12 |
| CNF \& DNF warmup            | 10 |         |           10 |
| total                        | 85 | 2.0     |           87 |
```

The default expects a bracket at the front of a `\prob{...}` title, and
reads both spellings:

```latex
\prob{[20 pts (8, 12)]: Bayes Net}
\prob{[16 points (4 pts each)]: Ecology System}
```

If that is not your convention, a `[points]` table in the `pset.toml` at
your repo root overrides it for every document underneath.  The keys are
sum-pts' own parameters, so its documentation is the reference:

```toml
[points]
prefix = ' *\\question'
points = '(marks|pts?)'
```

When the patterns do not fit, pset says so and links to
[docs/points.md](docs/points.md), which explains each key and the traps.
Points are read from the source, so `-p` still reports on a document that
failed to build.
