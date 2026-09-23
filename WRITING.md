# Writing for Wigner Time

How to write the prose that people outside the development team read. Set by the maintainer on
2026-09-23, after prose added to the manuscript since the arXiv version turned out to be written as
developer notes: too long, and hard for physicists to follow.

## Which documents

| register | documents | written for |
| --- | --- | --- |
| **Reader-facing** | `docs/paper/main.tex`, `README.md`, `docs/index.md`, onboarding documents, the front pages of the documentation | a physicist who writes Python |
| **API reference** | docstrings (rendered into `docs/api.md`), error messages | a user looking up one function |
| **Developer notes** | `CLAUDE.md`, `KNOWN_ISSUES.md`, `docs/origin-resolution.md`, code comments, commit messages | ourselves |

The rules below govern the first row. The API reference can be more technical: programming
vocabulary is fine there. Developer notes are where the history of the code and the detail of its
mechanism belong. Keeping those out of the reader-facing documents is what keeps them readable.

## The reader

An experimentalist in atomic physics, typically a PhD student, who writes Python every day but is
not a software engineer. They know *function*, *argument*, *keyword argument*, *default*, *list*,
*dictionary*, *loop*, *error*, *table*, *row*, *column* and *DataFrame*. They also know the terms the
paper introduces and defines: *timeline*, *stage*, *anchor*, *context*, *origin*, *deferred function*.

They do not know *namespace*, *call site*, *positional*, *placement argument*, *currying*,
*sentinel*, *shadowing*, *unreachable* or a *terminal* call or chain, and they should not have to.
If a term appears neither in the arXiv version of the paper nor in an ordinary physics paper, replace
it with plain words or define it where it first appears.

## Rules

1. **Say what the software does, not what it used to do.** "Raises an error", full stop. The bug a
   rule replaced, the old default, the behavior before a fix ("no longer", "now", "rather than being
   quietly dropped", "used to") are history, and the reader never met them. History belongs in commit
   messages and `KNOWN_ISSUES.md`.

2. **State the rule, give at most one reason, and stop.** A reason earns its place when it concerns
   the physics (a flat ramp is kept because it is a hold) or the reader's own choices (a stage should
   name its arguments, because a misspelled one would become a new variable). Leave out mechanism the
   reader cannot act on: sort orders, matching algorithms, which internal step filters which rows.

3. **Prefer an example from the paper's own experiment to an abstract qualification.** "Where one
   stage name begins another, as `MOT` begins `MOT_detuned_growth`" says in one clause what "where
   two stage names both anchor to an underscore boundary" does not say at all.

4. **No commentary on the prose itself.** Avoid "the distinction is worth stating because",
   "and deliberately", "precisely", "exactly as", and `\emph{is}` used for rhetorical weight. Use
   `\emph` for a term being introduced or for a genuine contrast, as the arXiv text does.

5. **If a behavior takes a paragraph of qualifications to describe, report it.** Do not write the
   paragraph. By the standing rule of `KNOWN_ISSUES.md` §G, prose that is awkward to write is a
   signal to change the code.

6. **A correction should be about as long as the claim it corrects.**

## Voice

The reference is the arXiv version of the manuscript (`git show fdd2e0d:docs/paper/main.tex`). For
example:

> Anchors are useful because key experimental time instants are often necessarily virtual. An anchor
> marks a moment that matters physically but that no device update records. The commonest case is a
> stage that ends in a waiting period: a MOT collection or a molasses stage finishes not because
> something is switched, but because enough time has passed.

Physical situations come first and the software's terms follow them. Each sentence carries one idea.
Any term the reader might not know is defined once, on first use, and then used consistently. New
prose should not be distinguishable from the text around it.

## Typography

- **Unicode, not LaTeX ligatures.** Use the en dash `–` for every dash: spaced for a parenthesis
  ("a stage – any stage – ends"), unspaced between two words that name a pair (client–server). Never
  write `--`, `---` or the em dash `—`.
- **Quotes and apostrophes** are `“ ”` and `’`, not ` `` '' ` or a straight `'`.
- **Units**: type `µ` directly, and put a thin space between number and unit in LaTeX (`1\,µs`,
  `0.1\,s`). Use `$…$` for inline mathematics, not `\(…\)`. In running text, "about 0.1\,s" reads
  better than `$\sim$0.1\,s`.
- **Spelling** is American: *-ize*, *analog*, *behavior*. The arXiv text is overwhelmingly American;
  its "initialises" and "behaviour" are strays.
- **In Markdown**, type the same characters directly. Do not use HTML entities (`&rsquo;`) or
  LaTeX.
- **Code is exempt**: anything inside `\python{}`, a `minted` block, backticks, a docstring or a
  comment can stay ASCII.

## Before and after

From the pass of 2026-09-23, which rewrote the post-arXiv additions to the manuscript:

> **Before.** Routing is strict. A keyword that names no stage, or that names one but is not a
> parameter of it, raises rather than being quietly dropped -- a dropped keyword would leave the
> stage on its default, which is a physically different sequence that nonetheless runs. The check is
> derived rather than configured: … Matching is anchored to the start of the keyword and to an
> underscore boundary, …
>
> **After.** Routing is strict: a keyword that matches no stage, or none of the parameters of the
> stage it matches, raises an error – unless that stage accepts arbitrary keywords, as `init` and
> `finish` do. Where one stage name begins another, as `MOT` begins `MOT_detuned_growth`, the longer
> name is tried first.

The rewrite drops the history ("rather than being quietly dropped") and the mechanism ("derived
rather than configured", "underscore boundary"). It replaces an abstract rule with the demo's own
case and fixes the ligature.

> **Before.** Since that keyword namespace *is* the variable namespace, there is deliberately no
> second, positional way of naming one: an unrecognised keyword is read as a variable rather than
> rejected, so a parallel syntax would be a second thing for it to be confused with.
>
> **After.** Any other keyword is read as the name of a variable.

## Checklist

Before committing reader-facing prose:

```bash
grep -n -E ' -- |---|—|namespace|\bpositional|call site' docs/paper/main.tex
grep -n -E ' -- |—|&[a-z]+;|namespace|\bpositional|call site' README.md docs/index.md
```

Each hit needs a reason to stay. Then read the passage as the reader described above would, at first
pass: rewrite anything that needs a second reading, and cut any sentence they could not act on.
