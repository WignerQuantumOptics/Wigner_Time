# Origin resolution: the complete branch map

Reference for the `origin` mechanism branch by branch.

**Every item in it is now implemented (2026-09-18).** The document is therefore no longer a plan but
a record: each table describes the code *as it was*, because the measurements in them are the
argument for what replaced it, and each entry says what it became. Read **The semantics, as
implemented** for the design as it now stands; read the tables when you want to know why.

One thing outstanding, and it is not code: `fig:origin` needs redrawing (#123). Its caption was
amended and the image was not, so they now contradict each other.

**Status.** Developer reference, not published documentation — it cites defects by their
`KNOWN_ISSUES.md` identifiers and is deliberately absent from the `mkdocs.yml` nav. The user-facing
account is `docs/paper/main.tex`, `sec:origin` and appendix `sec:origin_full`, and since
2026-09-18 the two agree.

**Provenance.** Every row below was verified by direct experiment against branch `drop_repeats`
(34104ce) on 2026-09-03, not inferred from reading. Where behaviour contradicts the manuscript or the
decision-tree figure, that is stated.

**All five steps of the suggested order landed on 2026-09-18**, in seven commits from `fba0fe0` to `dcda171`. The suite went 248 -> 288, and the demo and lab timelines hash identically throughout: every change either refuses something that was silently wrong, or corrects a case neither of them exercises.

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
| `ramp` (start point) | its own `[["anchor", "variable"]]` — anchor-only, and value-relative. **Now `config.ORIGIN__DEFAULTS__RAMP = [["anchor", "variable"], ["last", "variable"]]`** |
| `ramp` (`origin2`) | literal `["variable"]`; `auto` not called. **Now `["variable", 0.0]`** — the value slot stated rather than left to be read as `None`, since a ramp's end value is always absolute |

`auto` returned an explicitly supplied origin **untouched**; otherwise the first default entry whose
anchor requirement was satisfiable, and running off the end of the list returned `None` implicitly.

**Now:** `auto` normalises the given origin to a pair and fills, per slot, whichever slot the caller
left as `None`. The time default is a chain — each entry's time reference tried in turn, skipping
what this timeline cannot satisfy — and it is **terminal**: if nothing is satisfiable the time
origin is `0.0`, with a warning. The value default comes from the same entry. `auto` can no longer
return `None` implicitly.

Defects:

- ~~**A6** — an explicit origin *replaces* the default wholesale instead of completing it. Since a bare
  string normalises to `[s, None]` (Layer B), `ramp(..., origin="stage1")` silently loses its value
  default and starts the ramp from `0.0`.~~ **Fixed 2026-09-18** (#104), by per-slot completion. The
  vocabulary change that makes it coherent: `None` in a slot means *defer*, `0.0` means *absolute*.
- ~~**A4** — the fall-through. `ramp`'s anchor-only default has no `"last"` step, so on an anchorless
  timeline `auto` returns `None` and the rows land at absolute time.~~ **Fixed 2026-09-18** (#102) —
  the maintainer chose fall-back over raise, so `ramp` gained the `"last"` step and the chain gained
  a terminal `0.0` with a warning.
- ~~**NEW-9** — the same condition is handled two different ways: an *explicit* `origin="anchor"` on an
  anchorless timeline raises `anchor is an unsupported option`, while the *default* path is silent.~~
  **Fixed 2026-09-18.** The explicit path raises a message naming the missing anchor; the default
  path walks the chain, as documented. They now differ deliberately rather than accidentally.
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
| `"ctx"` | `["ctx", None]` | strings are not treated as iterable — this was A6's mechanism; the padding is unchanged, but `None` now means *defer*, so the padding no longer cancels anything |
| `["a"]` | `["a", None]` | |
| `["a", "b"]` | unchanged | |
| `("a", "b")` | unchanged, still a tuple | works via sequence patterns; undocumented |
| `["a", "b", "c"]` | `ValueError` | ~~**NEW-2**: message reads "Two many arguments"~~ **Fixed 2026-09-18** (#124): it now names the origin rather than the helper |

~~`find` performs this normalisation **twice** — once at the top for the `[None, None]` early return,
then again through `sanitize_origin`.~~ **Fixed 2026-09-18** (#124): once, through `sanitize_origin`,
so the "a string origin needs a timeline" check does gate the early return.

## Layer C1 — the time slot

Resolved by `origin.find` via `_to_col_var`.

| given | resolves to | defect |
| --- | --- | --- |
| `None` | no time shift | |
| a float | that number, added to all times | |
| `"anchor"` | the time of the most recent anchor-labelled row | raises if no anchor exists — **since 2026-09-18 with a message that says so**, rather than `unsupported option` |
| `"last"` | the time of the highest-time row | ~~**NEW-3**: on an empty timeline, `ValueError: attempt to get argmax of an empty sequence`~~ **Fixed 2026-09-18** (#115): `previous` names the empty timeline. The default path no longer reaches it — `"last"` is skipped as unsatisfiable and the chain runs to its terminal `0.0` |
| `"variable"` | per variable: that variable's own most recent time | **NEW-4**: substituted only inside `origin.update`'s per-variable loop. **Settled 2026-09-18** (#122): `find` *cannot* resolve it — it means "whichever variable is being placed", and `find` resolves one origin for the frame as a whole — so it now says that, and says where the substitution happens |
| an existing variable name | that variable's most recent time | |
| an existing context name | that context's anchor if it has one, else its last row | matches the figure |
| anything else | `error__unsupported_option` | loud, correct |

Precedence is `"anchor"` → `"last"` → variable name → context name.

- ~~**NEW-5** — reserved words shadow real names. With a context literally named `anchor` (rows at
  t=1) and a real anchor at t=5, `origin="anchor"` resolves to **5.0**.~~ **Fixed 2026-09-18**
  (#107). `_ORIGINS` is now derived from `_ORIGINS__TIME` rather than being a third list that can
  drift, and `timeline._populate_timeline` refuses a variable or context named after one of them —
  at the point the name is written, not where it later fails to resolve.

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
than the variable's last value in the timeline as a whole (`sec:origin_full`). It *was* computed
differently in two branches, and both were defective.

**Now there is one rule.** The time slot is resolved first, and the bound is
`resolved_t + fragment's earliest new time + TIME_RESOLUTION` — the instant the new rows will
occupy — computed **once**, before the per-variable loop.

| branch | bound | defect |
| --- | --- | --- |
| `[float, str]` | `n1 + time__max__relative` | **NEW-7**: if `n1 is None`, `TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'`. So a value-only origin against a variable is unusable through the public API. If `n1` is small, the bound excludes every past row and the error is `Previous <var> not found`, naming neither the bound nor the instant. |
| `[str, str]` | `resolved_t + TIME_RESOLUTION + time__max__relative` | |

- ~~**B2** — `time__max__relative` is `timeline__future["time"].min()`, recomputed **inside**
  `find_every_origin`'s per-variable loop while `_update_future` mutates those same times.~~
  **Fixed 2026-09-18** (#109) by hoisting. It was not merely inconsistent but wrong: in the
  regression case a variable now resolves to the value it actually held at the fragment's instant,
  where before the loop's own mutation pushed the bound past a later step.

### The maintainer's settlement, 2026-09-18

Two things were decided, and together they reduced steps 2 and 3 to one change rather than five
patches. Both are implemented; the present tense below is the design as it now stands, except where
it says "today", which describes what was replaced.

**The bound.** The value slot is *always* bounded by the resolved time origin — the value that variable held at that instant, never its last value in the timeline as a whole. The time slot is unbounded, because it resolves *to* the instant the bound is made of. This is already what the `[str, str]` branch does (measured: `["stage1", "variable"]` yields stage1's value, not the timeline's last), so it is the implementation that has to catch up with the design, not the reverse.

**`None` versus `0.0`.** In either slot, `None` means *defer to the caller's default for this slot* and `0.0` means *absolute, no shift*. Today `None` means absolute, which is the whole mechanism of A6: a bare `"stage1"` pads to `["stage1", None]` and so cancels `ramp`'s value default. Under the new reading `[None, "variable"]` and `["anchor", "variable"]` coincide wherever an anchor exists, and the former is the better spelling, since it does not name a reference it cannot guarantee. Blast radius checked: nothing in the lab, the demo or the tests passes a `None` time slot through the public API; `test_origin.py:91` calls `find` directly, below where completion happens.

## Layer D — application of the resolved pair

`_update_future` applies the pair **additively** (`+=`) to both time and value — per variable when a
variable is named, globally otherwise. The paper's own example confirms additive value semantics
(`origin=[1.0, 4.0]` with a value of 0.5 gives 4.5).

- ~~**NEW-8** — the value origin is added on top of an **explicitly stated** ramp start value.~~
  **Fixed 2026-09-18** (#106): resolved only for `df__no_start_points`. Briefly thought to be blocked
  on an idiom in `test_ramp_combined`; that test turned out to be a 2025-03 translation of the old
  `wait` mechanism, and `ramp(v=target, t=..., duration=...)` says the same thing.
- ~~**B1** — `ramp`'s degenerate-row mask aligns `new1` against `new2` by position, but with mixed
  1-D/2-D input the two frames carry different variable orders.~~ **Fixed 2026-09-18** (#108) by
  aligning on `variable` first. The consequence was worse than a wrong comparison, because A3 turned
  the mask into a deletion: a call in which nothing was degenerate lost its **entire** ramp, because
  positionally each variable's start matched the *other*'s end in value.
- ~~**A3** — the cleaned frames are computed and then discarded.~~ **Settled and fixed 2026-09-18**
  (#101), by maintainer decision: the two degeneracies are not alike and are now split. A zero
  **duration** raises; a zero **value change** is a *hold*, occupies time, and is kept and expanded,
  the redundancy being removed again by `drop_repeats` before the hardware.
- **A12** — found while reviewing that guard, and the worst of the three. A **negative** duration was
  accepted, and because `expand` sorts each ramp's rows by time before pairing them, the endpoints
  were silently **exchanged**: `ramp(c__A=9.0, duration=-1.0)` left the variable at its old value
  rather than at 9.0, and laid the transition across the second *preceding* the origin. **Fixed
  2026-09-18** (#135): the guard tests the signed duration rather than its magnitude.

---

## The semantics, as implemented

Stated positively. This was written as a target and is now a description: all six items landed on
2026-09-18, and the notes under each say what it cost to get there.

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

Only the `"anchor"` third of this was a straight defect — the `fig:origin` caption already said no
value is defined for anchors, so returning `0.0` contradicted the documented design. Narrowing
`"last"` and context names needed that caption amended first. **The maintainer declared the caption
defective on 2026-09-18**, so all three were narrowed together and the caption rewritten; the image
still has to follow (#123).

**2. Defaults complete a partial origin per slot, rather than replacing it.** For each slot, if the
caller left it `None`, take the caller's default for that slot. `update` and `anchor` default the
value slot to absolute; `ramp` defaults it to `"variable"`. This closes A6 and makes
`ramp(..., origin="stage1")` mean what it reads as.

The vocabulary this rests on, and the part most likely to surprise: **`None` in a slot means *defer*
to the default for that slot, and `0.0` means *absolute***. They used to mean the same thing, which
is exactly why the padding of a bare string cancelled `ramp`'s value default.

**3. The time default is a chain owned by the caller, not a config constant:**
`anchor` → `last` → `0.0` with a warning. Keeping the `"last"` step matters — dropping it would place
rows *before* the timeline they were appended to, which is A4's symptom merely made audible. The final
`0.0` step covers the empty timeline, where `"last"` is unresolvable (NEW-3).

**4. One definition of the lookup bound**, for both branches: *the instant the new rows will occupy
once the time origin is applied*. This removes NEW-7 and makes the two branches agree. Compute
`time__max__relative` once, before the loop (B2). The time slot is resolved first, so that it can
be what the bound is built from; the time slot itself is never bounded, because it resolves *to*
the instant.

**5. Never apply a value origin to a row whose start value the user stated explicitly** — resolve it
only for variables in `df__no_start_points`, never for `df_1` (NEW-8).

**6. Promote `_ORIGINS` to the single source of reserved words**, and reject a variable or context
name that shadows one (NEW-5). It is now derived from `_ORIGINS__TIME`, the wider of the two slot
vocabularies, so there is no third list to drift.

**7. Guards on `ramp`'s boundaries, added alongside the above.** Not part of the origin mechanism,
but in the same block of `ramp` and settled with it: a ramp must end after it begins (zero and
negative durations both raise, A3 and A12), a ramp whose value does not change is a *hold* and is
kept, a start value stated in the 2-D form is taken as written, and a variable with no previous
entry has no start point and raises. All four are now stated in the manuscript, in
`sec:functions`'s "What a ramp refuses".

## The order it was done in

1. ~~Slot vocabularies and reserved-word handling (NEW-5, NEW-6). Pure validation — no behaviour change
   for code that is already correct.~~ **Done 2026-09-18.** 268 tests pass; the demo and the lab
   timelines are unchanged, as they must be — the change only refuses, it never resolves differently.
2. ~~Bound unification and hoisting (NEW-7, B2).~~ **Done 2026-09-18.** One bound for both
   branches, built from the *resolved* time origin and computed once before the loop.
3. ~~Per-slot default completion and the caller-owned chain (A6, A4, NEW-9, NEW-1).~~ **Done
   2026-09-18.** The blast radius estimate held: two tests changed, both of which had encoded the
   defects (`test_originAuto2` the implicit `None`, `test_stack` the absolute landing). The demo and
   lab timelines hash identically before and after.
4. ~~NEW-8~~ **done 2026-09-18** — the value origin is resolved only for `df__no_start_points`. It was
   briefly thought to be blocked on an idiom in `test_ramp_combined`; that test turned out to be a
   2025-03 translation of the old `wait` mechanism, and `ramp(v=target, t=..., duration=...)` says the
   same thing. **B1 done 2026-09-18** — the boundary frames are aligned on `variable` before being
   subtracted; the defect was not merely a wrong comparison but a silent deletion of the whole ramp,
   because A3's early return acts on the bad mask. **A3 done 2026-09-18**, by maintainer
   decision: the two degeneracies are split — a zero duration raises, a zero value change is a hold
   and is kept. That closes the block.
5. ~~Diagnostics: NEW-2, NEW-3, NEW-4, and the `Previous <var> not found` message.~~ **Done
   2026-09-18.** `previous` names an empty timeline; a variable with no history says so; the
   `ensure_pair` message names the origin rather than the helper, and `find` normalises once;
   `"variable"` reaching `find` directly explains that it is substituted per variable upstream.

## Manuscript implications

All of these were carried out on 2026-09-18, so this section now records **what changed in
`docs/paper/main.tex` and what still has to** — the latter being one item, and not a text edit.

Done:

- **The `fig:origin` caption.** It read "With the exception of anchors, for which no value is defined,
  every option can serve as either a time or a value origin", which excluded `anchor` from the value
  slot (the code did not honour even that, returning the anchor's dummy `0.0`) but positively licensed
  `"last"` and context names there. Narrowing those was a manuscript change, not a bug fix; **the
  maintainer declared the caption defective and opened the gate**. It now states the slot split, and
  says why nothing is lost: `["molasses", "variable"]` expresses what a context in the value slot was
  reaching for.
- **`sec:origin_full`'s claim that no default is value-relative.** It was false, and had been all
  along: `ramp`'s start-point default is value-relative, and that is the reason ramps chain. The
  sentence now names the exception before making the general statement.
- **The default described as anchor-else-most-recent-entry, in both `sec:origin` and
  `sec:origin_full`.** Both now carry the terminal step — absolute time with a warning — and the
  appendix additionally states that the slots are completed independently, and hence that `None` means
  "use the default here" while absolute placement is `0.0`.
- **`origin2`'s default**, quoted in `sec:origin_full` as `["variable"]`, now `["variable", 0.0]`.
- **A new paragraph in `sec:functions`, "What a ramp refuses"**, covering the guards settled with this
  block: zero and negative durations raise, a flat ramp is a hold and is kept, a variable with no
  previous entry has no start point, and a stated start value is taken as written.

Outstanding, and it blocks submission:

- **`graphic/origin-decision-tree-highlighted.png` has to be redrawn** (#123). Its caption was amended
  and the image was not, so the figure now contradicts itself. Three things need to change in it: the
  root node should read `None` rather than `0.0` in the value slots; the resolution should be shown
  per slot rather than as one flat tree serving both; and the chain should show its terminal step. The
  figure's existing leaf wording already leans the right way — `"last"` and `"anchor"` are described
  as *times*, the value-capable leaves neutrally as *entities* — so the redraw is a clarification of
  what it was reaching for, not a reversal.
