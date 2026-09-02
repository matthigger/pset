# Writing a point-counting config

`pset -p` sums the points per problem by handing your document to
[sum-pts](https://github.com/matthigger/sum_pts). If you got here from an
error message, the patterns it was given did not fit your document.

## What pset assumes by default

Out of the box pset expects the points to sit in a bracket at the front of
a `\prob{...}` title:

    \prob{[20 pts (8, 12)]: Bayes Net}
    \prob{[16 points (4 pts each)]: Ecology System}

Both of those work unchanged. The bracket holds the problem total; the
parenthesised per-part split, the braces and the trailing colon are stripped
so only the total is summed. You do **not** need a config to switch between
`pts` and `points` — sum-pts matches both.

The defaults are exactly:

| key | default | meaning |
|-----|---------|---------|
| `left` | `'\['` | regex matching the start of the point block |
| `right` | `'\]'` | regex matching the end of the point block |
| `prefix` | `' *\\prob'` | regex matching the start of a line that has points |
| `rm_list` | see below | regexes stripped from the line before reading it |

`rm_list` defaults to the per-part split and the LaTeX punctuation:

    ['\(\d+.?\d* each\)', '\((\d+.?\d*,? ?)+\)', '\{', '\}', ':']

Anything not listed above keeps [sum-pts' own
default](https://github.com/matthigger/sum_pts) — in particular `points`,
which already matches `pt`, `pts`, `point` and `points` in either case.

## Overriding them

Put a `pset.toml` at the root of your problem repo. It applies to every
document underneath, so one file per repo is normally enough.

```toml
[points]
prefix = ' *\\question'
```

Use TOML *literal* strings (single quotes) for patterns. In a literal string
a backslash is just a backslash, so you write the regex exactly as you would
in a `grep` argument. In a normal double-quoted string you would have to
double every backslash.

Keys are passed straight through to sum-pts, so its parameters are the full
list of what you can set:

| key | what it does |
|-----|--------------|
| `left`, `right` | delimit the point block |
| `prefix` | picks out lines that carry points |
| `points` | matches the word "points" or similar |
| `pt_split` | splits point *types* apart, e.g. normal vs extra credit |
| `rm_list` | regexes discarded from the line |
| `ignore_case` | `true` to make every pattern case-insensitive |

`pt_split` defaults to `'[+&,]'`, which is what makes

    \prob{[16 pts (4, 4, 4, 4) + 2 extra]: Modular Arithmetic}

report 16 points and 2 extra separately.

### One trap worth knowing

If you override `points` with an alternation, parenthesise it. sum-pts
interpolates your pattern into a larger regex, so a bare `|` splits that
whole regex rather than just your alternatives:

```toml
[points]
points = 'pts|marks'      # wrong: corrupts the surrounding regex
points = '(pts|marks)'    # right
```

## Checking a config

`pset -p` prints the table it derived, so the fastest check is to run it on
one document you know the total of. A count that comes back suspiciously low
usually means a pattern matched something narrower than you meant — the
totals are not validated against anything, so nothing will complain for you.
