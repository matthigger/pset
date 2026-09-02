# Using this problem repo

Every problem lives in its own `.tex` file under `problems/`, carrying its
solution and rubric alongside the question.  An assignment is a short file
that sets the metadata and `\input`s the problems it wants.  Problems are
reused across terms and instructors; assignments are not.

This repo is built with [pset](https://github.com/matthigger/pset):

    pip install pset

## Building an assignment

From the assignment's own folder, name it without the suffix:

    cd hw_example
    pset hw_example

That writes three PDFs from the one source: `hw_example.pdf` for the
students, `hw_example_sol.pdf` with the answers, `hw_example_rub.pdf` with
the grading rubric.  A copy the document has no content for is skipped and
says so.  `--no-sol` and `--no-rub` refuse one outright, `-p` adds the
point total per problem, and arguments may be globs or folders:

    pset quiz1*          # every version at once
    pset exam1/          # every document in a folder

## Writing a problem

Put it in the topic folder it belongs to, named so a variant can join it
later (`base_convert01.tex`, then `base_convert02.tex`).  Write only the
body: no `\documentclass`, no `\begin{document}`, since the assignment
supplies both.  Three macros divide the content.

    Convert 635 from decimal to binary.

    \stud{\vfill}

    \sol{$635 = (1001111011)_2$}

    \rub{3 pts for the answer, 3 for the work.}

Each copy is that one source with a different subset switched on:

| macro | student | `_sol` | `_rub` | what goes in it |
|-------|---------|--------|--------|-----------------|
| plain text | yes | yes | yes | the question |
| `\stud` | yes | | | space for the work |
| `\sol` | | yes | yes | the answer |
| `\rub` | | | yes | how to mark it |

So `\sol` shows only in the solution and rubric copies and `\rub` only in
the rubric.  `\stud` runs the other way: it is the student-only content,
dropped from both keys.  Mostly that is the blank space left for the work,
`\stud{\vfill}` or `\stud{\vspace{2in}}` after the question, which the
answer key does not want: leave it in and every answer sits alone on its
own page, so grading one problem means paging through five sheets.
Anything else addressed only to the student goes in it too, such as
`\stud{Show your work.}` or a table to fill in.

All three wrap their content rather than switching a mode, so each takes
an argument: `\stud{...}`, not `\begin{stud}`.  They nest, so
`\sol{... \rub{...}}` hangs a per-part rubric off the answer it belongs to.

Two conventions keep the paths workable.  Write the `.tex` suffix in every
`\input{}`, so an editor can follow the reference, and give each
assignment its own folder beside `hw_example`, so `../problems/...`
resolves the same way from all of them.  Every problem shares the one
`packages.tex`, so be conservative about adding to it: a package added
today is required of every assignment anyone builds afterwards.

## Reading what is already here

    pset --browse

renders every problem into `problems_pdf/`, one PDF per topic folder, with
the solutions shown.  Worth doing before writing a new problem, and it
catches any problem that has stopped compiling.

## Checking what you have already used

    pset --usage

writes `prob_file_pair.json`, pairing each problem with the assignments
that `\input` it and each assignment with its problems.  It flags any
problem used more than once, which is how the same question ends up on
both the homework and the exam, and counts the ones never used.  Run it
from anywhere in the repo.
