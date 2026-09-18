# Origin resolution: the complete branch map

Reference for the `origin` mechanism as **implemented**, branch by branch, with the defects found in
each and a suggested target semantics.

**Status.** Developer reference, not published documentation — it cites unfixed defects by their
`KNOWN_ISSUES.md` identifiers and is deliberately absent from the `mkdocs.yml` nav. The user-facing
account is `docs/paper/main.tex`, `sec:origin` and appendix `sec:origin_full`.

**Provenance.** Every row below was verified by direct experiment against branch `drop_repeats`
(34104ce) on 2026-09-03, not inferred from reading. Where behaviour contradicts the manuscript or the
decision-tree figure, that is stated.

**Steps 1 to 3 of the suggested order landed 2026-09-18.** Layers A, B (as read by `auto`), C2 and the lookup bound have all changed; the tables below describe the code *before* those changes and are kept because the measurements are the argument for them. What replaced each is recorded inline. Remaining: step 4 (A8 — **blocked on a maintainer decision**, see KNOWN_ISSUES; then B1 and A3) and step 5 (diagnostics NEW-2 and NEW-4).

**Step 1** (slot vocabularies and reserved words, A7/#105 and A9/#107). The Layer C2 table below therefore describes what the code did *before* that change; it is kept because the measurements are the argument for the narrowing. Rows now refused are marked **REFUSED**. Steps 2 and 3 are being taken together, per the maintainer's settlement of the lookup bound (see the note at the end of Layer C2).

**Re-verified 2026-09-17.** The measured tables still hold, with one correction below and one
substantive change: `create` no longer takes `origin` or `timeline` at all (#45 / C2), so Layer A has
one fewer entry and one fewer defect. Every `NEW-n` identifier used here is tracked as a GitHub
issue — NEW-1 #123, NEW-2 #124, NEW-3 #115, NEW-4 #122, NEW-5 #107, NEW-6 #105, NEW-7 #114,
NEW-8 #106, and NEW-9 inside #102 (A4) rather than as an item of its own.

**The figure.** `docs/paper/graphic/origin-decision-tree-highlighted.png` is the authoritative
diagram (`fig:origin`), and its caption is the authoritative statement of which slots each option
may serve. **The caption was amended on 2026-09-18 to state the slot split; the image was not,
and cannot be from here — it still draws one undivided tree, so it now contradicts its own
caption and needs redrawing before submission.** It presents resolution as one flat tree. This document splits it into **four layers**,
because the flat presentation hides where the defects live: the tree describes Layer C only, and says
nothing about which default was selected (A), how a scalar becomes a pair (B), or how a resolved pair
is applied (D).

---

## Layer A — entry: which default applies

| caller | default handed to `origin.auto` |
| --- | --- |
| `create` | **not applicable — it takes no `origin` and no `timeline`** (#45, 2026-09-16) |
| `update`, `anchor` | `config.ORIGIN__DEFAULTS = [["anchor", None], ["last", None]]` |
| `ramp` (start point) | its own `[["anchor", "variable"]]` — anchor-only, and value-relative |
| `ramp` (`origin2`) | literal `["variable"]`; `auto` not called |

`auto` returns an explicitly supplied origin **untouched**; otherwise it returns the first default
entry whose anchor requirement is satisfiable. Running off the end of the list returns `None`
implicitly.

Defects:

- **A6** — an explicit origin *replaces* the default wholesale instead of completing it. Since a bare
  string normalises to `[s, None]` (Layer B), `ramp(..., origin="stage1")` silently loses its value
  default and starts the ramp from `0.0`.
- **A4** — the fall-through. `ramp`'s anchor-only default has no `"last"` step, so on an anchorless
  timeline `auto` returns `None` and the rows land at absolute time.
- **NEW-9** — the same condition is handled two different ways: an *explicit* `origin="anchor"` on an
  anchorless timeline raises `anchor is an unsupported option`, while the *default* path is silent.
- ~~**C2** — `create` consults no default at all, even when given a timeline.~~ **Resolved
  2026-09-16**: `create` initialises a timeline from scratch and now takes neither argument, which is
  the signature `sec:functions` documented all along. There is nothing for it to be relative to, so
  no default applies. To extend a timeline, use `update`.
- ~~**NEW-1** — the figure's root node reads `[["anchor", 0.0], ["last", 0.0]]`; the config has `None`
  in both value slots.~~ **Settled 2026-09-18**: they no longer disagree in substance, because
  `None` now means "defer to the default for this slot" while `0.0` means "absolute" — and for a
  value slot whose default is absolute, the two coincide. The figure still needs redrawing for the
  slot split (see **The figure**), and its root node should read `None` when it is.

## Layer B — normalisation to a `[time, value]` pair

`ensure_pair(ensure_iterable_with_None(origin))`, both in `internal/util.py`.

| input | result | note |
| --- | --- | --- |
| `None` | `[None, None]` | |
| `[]` | `[None, None]` | undocumented |
| `0.5` | `[0.5, None]` | a single value is a **time** origin |
| `"ctx"` | `["ctx", None]` | strings are not treated as iterable — this is A6's mechanism |
| `["a"]` | `["a", None]` | |
| `["a", "b"]` | unchanged | |
| `("a", "b")` | unchanged, still a tuple | works via sequence patterns; undocumented |
| `["a", "b", "c"]` | `ValueError` | **NEW-2**: message reads "Two many arguments" |

`find` performs this normalisation **twice** — once at the top for the `[None, None]` early return,
then again through `sanitize_origin`. Harmless, but it means `sanitize_origin`'s timeline check does
not gate the early return.

## Layer C1 — the time slot

Resolved by `origin.find` via `_to_col_var`.

| given | resolves to | defect |
| --- | --- | --- |
| `None` | no time shift | |
| a float | that number, added to all times | |
| `"anchor"` | the time of the most recent anchor-labelled row | raises if no anchor exists (NEW-9) |
| `"last"` | the time of the highest-time row | **NEW-3**: on an empty timeline, `ValueError: attempt to get argmax of an empty sequence`, raised from `dataframe.row_from_max_column` |
| `"variable"` | per variable: that variable's own most recent time | **NEW-4**: substituted only inside `origin.update`'s per-variable loop; passed straight to `find` it raises |
| an existing variable name | that variable's most recent time | |
| an existing context name | that context's anchor if it has one, else its last row | matches the figure |
| anything else | `error__unsupported_option` | loud, correct |

Precedence is `"anchor"` → `"last"` → variable name → context name.

- **NEW-5** — reserved words shadow real names. With a context literally named `anchor` (rows at
  t=1) and a real anchor at t=5, `origin="anchor"` resolves to **5.0**. A context named `anchor`,
  `last` or `variable` is unreachable as an origin. `_ORIGINS = ["anchor", "last", "variable"]` exists
  in `origin.py` to document exactly this and is referenced nowhere.

## Layer C2 — the value slot

Same resolver, different meaning — and this is where the mechanism over-generated. The paper's
position *was*, from the `fig:origin` caption: "With the exception of anchors, for which no value
is defined, every option can serve as either a time or a value origin." That made `"anchor"` here a
defect against the documented design, while `"last"` and context names were licensed by it.

**Settled 2026-09-18.** The maintainer declared the caption defective, so all three were narrowed
together and the caption rewritten. The table below records what the code did before that, because
the measurements are the argument for the change.

| given | resolves to | verdict |
| --- | --- | --- |
| `None` | value untouched (absolute) | correct |
| a float | added to all values | correct |
| `"variable"` | that variable's own last value, time-bounded | **meaningful** — `ramp`'s default |
| an existing variable name | that variable's last value, time-bounded | **meaningful** |
| `"anchor"` | `0.0` — the anchor row's dummy value | **REFUSED 2026-09-18** (#105) |
| `"last"` | the value of whichever variable holds the highest time | **REFUSED 2026-09-18** (#105), with the caption amended |
| a context name | the value of that context's last row, whatever variable that is | **REFUSED 2026-09-18** (#105), with the caption amended |
| anything else | raises | correct |

Measured, on a timeline with `coil__A` = 7.0 A, an anchor at t=5, and `shutter_MOT` = 1 at t=9:

```
origin=[20.0, "variable"]  -> 7.0   the variable's own last value
origin=[20.0, "coil__A"]   -> 7.0   same, named explicitly
origin=[20.0, "anchor"]    -> 0.0   the anchor's dummy value
origin=[20.0, "last"]      -> 1.0   shutter_MOT's state. In amps.
origin=[20.0, "prep"]      -> 1.0   the context's last row, whatever variable that is
```

The last line assumes `prep` holds **no anchor of its own**. Where it does, the context resolves to
that anchor instead and the value is the anchor's dummy `0.0` — the same NEW-6 defect reached by a
second route. Both were re-measured on 2026-09-17.

`"last"` is not even consistently wrong, because the answer depends on the lookup bound:

```
origin=[20.0, "last"]      -> 1.0   bound admits shutter_MOT at t=9
origin=["anchor", "last"]  -> 0.0   bound is the anchor's own instant, and the
                                    anchor IS the highest-time row there
```

### The time bound on value lookups

The bound exists so that an interwoven operation sees the state that *physically precedes* it, rather
than the variable's last value in the timeline as a whole (`sec:origin_full`). It is computed
differently in two branches, and both are defective.

| branch | bound | defect |
| --- | --- | --- |
| `[float, str]` | `n1 + time__max__relative` | **NEW-7**: if `n1 is None`, `TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'`. So a value-only origin against a variable is unusable through the public API. If `n1` is small, the bound excludes every past row and the error is `Previous <var> not found`, naming neither the bound nor the instant. |
| `[str, str]` | `resolved_t + TIME_RESOLUTION + time__max__relative` | |

- **B2** — `time__max__relative` is `timeline__future["time"].min()`, recomputed **inside**
  `find_every_origin`'s per-variable loop while `_update_future` mutates those same times. So which
  past value counts as "in effect" depends on what else is being resolved, and in what order. Adding
  an unrelated variable to a `ramp` call moved another variable's start value from 20.0 to 10.0.

### The maintainer's settlement, 2026-09-18

Two things were decided, and together they reduce steps 2 and 3 to one change rather than five patches.

**The bound.** The value slot is *always* bounded by the resolved time origin — the value that variable held at that instant, never its last value in the timeline as a whole. The time slot is unbounded, because it resolves *to* the instant the bound is made of. This is already what the `[str, str]` branch does (measured: `["stage1", "variable"]` yields stage1's value, not the timeline's last), so it is the implementation that has to catch up with the design, not the reverse.

**`None` versus `0.0`.** In either slot, `None` means *defer to the caller's default for this slot* and `0.0` means *absolute, no shift*. Today `None` means absolute, which is the whole mechanism of A6: a bare `"stage1"` pads to `["stage1", None]` and so cancels `ramp`'s value default. Under the new reading `[None, "variable"]` and `["anchor", "variable"]` coincide wherever an anchor exists, and the former is the better spelling, since it does not name a reference it cannot guarantee. Blast radius checked: nothing in the lab, the demo or the tests passes a `None` time slot through the public API; `test_origin.py:91` calls `find` directly, below where completion happens.

## Layer D — application of the resolved pair

`_update_future` applies the pair **additively** (`+=`) to both time and value — per variable when a
variable is named, globally otherwise. The paper's own example confirms additive value semantics
(`origin=[1.0, 4.0]` with a value of 0.5 gives 4.5).

- **NEW-8** — the value origin is added on top of an **explicitly stated** ramp start value. With
  `coil__A` last known at 7.0, `ramp(coil__A=[[0.0, 1.0], [0.5, 3.0]])` produces a start value of
  **8.0**, not 1.0 — yet `tab:rampExamples` documents that exact form as "for cases where the start
  cannot be inferred from `origin`".
- **B1** — `ramp`'s degenerate-row mask aligns `new1` against `new2` by position, but with mixed
  1-D/2-D input the two frames carry different variable orders, so it compares one variable's time
  against another's.
- **A3** — the cleaned frames are computed and then discarded. When *every* row is degenerate the
  early return drops the whole ramp silently.

---

## Suggested target semantics

Stated positively, as the thing to implement rather than as a list of patches.

**1. Split the vocabulary by slot.** This is the central change.

| slot | admits |
| --- | --- |
| time | a number, `"anchor"`, `"last"`, `"variable"`, a variable name, a context name |
| value | a number, `"variable"`, a variable name |

`"anchor"`, `"last"` and context names in the value slot **raise**. Unlike the time slot there is no
sensible value to fall back to, and nothing is lost: "the value `coil__A` held at the end of molasses"
is already expressible as `["molasses", "variable"]` — time from that context's anchor, value from
this variable bounded by that instant. `"variable"` ends up the only reserved word valid in both
slots. Several branches of `find`'s match become unreachable and can go.

Only the `"anchor"` third of this is a straight defect — the `fig:origin` caption already says no
value is defined for anchors, so returning `0.0` contradicts the documented design. Narrowing
`"last"` and context names needs that caption amended first, and is therefore the maintainer's
call rather than a bug fix.

**2. Defaults complete a partial origin per slot, rather than replacing it.** For each slot, if the
caller left it `None`, take the caller's default for that slot. `update` and `anchor` default the
value slot to absolute; `ramp` defaults it to `"variable"`. This closes A6 and makes
`ramp(..., origin="stage1")` mean what it reads as.

**3. The time default is a chain owned by the caller, not a config constant:**
`anchor` → `last` → `0.0` with a warning. Keeping the `"last"` step matters — dropping it would place
rows *before* the timeline they were appended to, which is A4's symptom merely made audible. The final
`0.0` step covers the empty timeline, where `"last"` is unresolvable (NEW-3).

**4. One definition of the lookup bound**, for both branches: *the instant the new rows will occupy
once the time origin is applied*. This removes NEW-7 and makes the two branches agree. Compute
`time__max__relative` once, before the loop (B2).

**5. Never apply a value origin to a row whose start value the user stated explicitly** — resolve it
only for variables in `df__no_start_points`, never for `df_1` (NEW-8).

**6. Promote `_ORIGINS` to the single source of reserved words**, and reject a variable or context
name that shadows one (NEW-5).

## Suggested order

1. ~~Slot vocabularies and reserved-word handling (NEW-5, NEW-6). Pure validation — no behaviour change
   for code that is already correct.~~ **Done 2026-09-18.** 268 tests pass; the demo and the lab
   timelines are unchanged, as they must be — the change only refuses, it never resolves differently.
2. ~~Bound unification and hoisting (NEW-7, B2).~~ **Done 2026-09-18.** One bound for both
   branches, built from the *resolved* time origin and computed once before the loop.
3. ~~Per-slot default completion and the caller-owned chain (A6, A4, NEW-9, NEW-1).~~ **Done
   2026-09-18.** The blast radius estimate held: two tests changed, both of which had encoded the
   defects (`test_originAuto2` the implicit `None`, `test_stack` the absolute landing). The demo and
   lab timelines hash identically before and after.
4. NEW-8, then B1 and A3 together — A3 currently masks B1. **NEW-8 is blocked**: the exemption was
   implemented on 2026-09-18 and backed out, because it removes the "hold at the current value, then
   ramp" idiom that `test_ramp_combined` relies on. See KNOWN_ISSUES A8 for the two readings and what
   each costs.
5. Diagnostics: ~~NEW-3~~ (done: `previous` names the empty timeline), NEW-2, NEW-4, and
   ~~the `Previous <var> not found` message~~ (done: a variable with no history now says so).

## Manuscript implications

- The narrowing in (1) needs the `fig:origin` caption amended, not just the figure. The caption
  (`main.tex:916`) reads "With the exception of anchors, for which no value is defined, every option
  can serve as either a time or a value origin" — so it already excludes `anchor` from the value slot
  (which the code does not honour: it returns the anchor's dummy 0.0), but it positively licenses
  `"last"` and context names there. Narrowing those is therefore a manuscript change requiring the
  maintainer's assent, not a bug fix. The figure's leaf wording leans the same way as the narrowing:
  `"last"` and `"anchor"` are described as *times*, the value-capable leaves neutrally as *entities*.
- `sec:origin_full` states "No default in the package is value-relative; value origins … are always
  requested explicitly." This is already false: `ramp`'s start-point default is
  `["anchor", "variable"]`, and that is the reason ramps chain correctly at all.
- `sec:origin` and `sec:origin_full` both describe the default as anchor-else-most-recent-entry, with
  no terminal fallback and no warning. Item (3) adds both, so both sentences need extending.
