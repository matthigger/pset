"""Report which problems appear in which assignments, and the reverse.

A problem library is only reusable if you can see what you have already
used.  This reads the \\input tree of every assignment in a repo and pairs
it against the problems, answering the two questions that matter when
building the next assignment: has this problem been used already, and what
have I never used at all.

The pairing is written to prob_file_pair.json as two objects:

    {file_to_prob: {assignment: [problem, ...]},
     prob_to_file: {problem: [assignment, ...]}}

Keys are repo-relative and suffix-free on both sides, so a problem reads
as number_rep/base_convert01 and an assignment as HW1_logic/hw1.  A
problem no assignment inputs keeps an empty list rather than dropping out,
which is what makes the unused ones greppable.
"""

import json
import pathlib
import re
from collections import defaultdict
from typing import Optional

from .config import PROBLEMS

OUT_NAME = 'prob_file_pair.json'

# An \input path, ignoring one commented out.  Only the % immediately
# before the macro is checked: a line commented further left is rare
# enough that following it costs less than parsing LaTeX properly.
INPUT = re.compile(r'(?<!%)\\input\{([^}]+)\}')

# Leading ../ hops and the problems/ folder, stripped so an \input written
# from an assignment folder lands on the same key as the problem's path
# relative to problems/.
PREFIX = re.compile(r'^[./]*' + PROBLEMS + '/')


def problem_keys(root: pathlib.Path) -> list[str]:
    """List every problem in a repo, by its key.

    Args:
        root: the repo root

    Returns:
        keys: paths relative to problems/, without the .tex suffix, e.g.
            number_rep/base_convert01
    """
    folder = root / PROBLEMS
    return sorted(path.relative_to(folder).with_suffix('').as_posix()
                  for path in folder.glob('**/*.tex'))


def assignment_files(root: pathlib.Path) -> list[pathlib.Path]:
    """List the .tex files in a repo that are not problems.

    Every .tex outside problems/ counts, which sweeps in the shared
    fragments (packages.tex, command.tex) alongside the assignments.  They
    input no problems, so they pair with nothing and fall out on their own.
    """
    return sorted(set(root.glob('**/*.tex'))
                  - set((root / PROBLEMS).glob('**/*.tex')))


def pair(files: list[pathlib.Path], keys: list[str],
         root: pathlib.Path) -> tuple[dict, dict]:
    """Pair assignments against problems, both ways.

    Args:
        files: the assignment .tex files to read
        keys: the problem keys to look for, from problem_keys
        root: the repo root, which the assignment keys are relative to

    Returns:
        prob_to_file (dict): {problem key: [assignment key, ...]}, every
            problem present, empty where none uses it
        file_to_prob (dict): {assignment key: [problem key, ...]}, only
            the assignments that use at least one problem
    """
    known = set(keys)
    prob_to_file = {key: [] for key in keys}
    file_to_prob = defaultdict(list)

    for path in files:
        name = path.relative_to(root).with_suffix('').as_posix()
        text = path.read_text(errors='ignore')
        for target in INPUT.findall(text):
            key = PREFIX.sub('', target)
            if key.endswith('.tex'):
                key = key[:-len('.tex')]
            if key in known:
                prob_to_file[key].append(name)
                file_to_prob[name].append(key)

    return prob_to_file, dict(file_to_prob)


def usage(root: Optional[pathlib.Path] = None,
          out: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Write a repo's problem-to-assignment pairing, and report on it.

    Prints the two things worth acting on: a problem used by more than one
    assignment, which is how the same question lands on both a homework
    and the exam, and how many problems are unused.

    Args:
        root: the repo root
        out: where to write, defaulting to prob_file_pair.json at the root

    Returns:
        out: the file written
    """
    keys = problem_keys(root)
    prob_to_file, file_to_prob = pair(assignment_files(root), keys, root)

    out = out or root / OUT_NAME
    with open(out, 'w') as file:
        json.dump({'file_to_prob': file_to_prob,
                   'prob_to_file': prob_to_file},
                  file, sort_keys=True, indent=4)

    print(f'{len(keys)} problems, {len(file_to_prob)} assignments '
          f'-> {out}')

    repeat = {key: used for key, used in sorted(prob_to_file.items())
              if len(used) > 1}
    for key, used in repeat.items():
        print(f'    repeated: {key} in {", ".join(used)}')

    unused = [key for key, used in prob_to_file.items() if not used]
    if unused:
        print(f'    {len(unused)} unused (grep the json for [])')

    return out
