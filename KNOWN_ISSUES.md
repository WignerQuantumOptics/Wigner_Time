# Wigner Time — known issues

Standing checklist for code work. Written for an agent picking up the repository cold.

**Provenance.** Originally derived from snapshots of `timeline.py` and `origin.py` plus design discussion. **Verified against the live repository on 2026-09-01, branch `drop_repeats` (34104ce).** Every item below was checked against the code as it stands; the ones that were reproduced empirically say so and give the repro. Line references are deliberately omitted; anchor on function names. Both **[verify]** items (A4, D1) are now resolved — see their entries.

**Priority order.** Silent failures rank above visible ones. A wrong answer that raises is a nuisance; a wrong answer that returns quietly can sit in an experiment for months.

Item IDs are stable — they are cross-referenced from `CLAUDE.md` and from C1 — so verification has *not* renumbered them, and sections A and B are consequently no longer in strict severity order. **A4 is now the most severe open item in this document**: it was expected to be unreachable and turns out to be reachable through `ramp`, silently, on any anchorless timeline. Read A4 first.

**Origins have their own reference.** `docs/origin-resolution.md` maps every branch of the origin mechanism as implemented, in four layers, with the defect in each. Read it before touching `internal/origin.py` — the items below give the defects, that document gives the shape.

**Do not "fix" by adding try/except or defensive branching.** This library's value proposition is that experiment descriptions are inspectable data. Failures should be loud and early, at the point where the user's intent was ambiguous — not absorbed downstream.

---

## A. Silent failures

### A1 — `cascade` discards unmatched keywords — **FIXED 2026-09-16**

`timeline.cascade`. The dispatch loop iterates over `kws`, tries each function name, and `break`s on the first match. If no function name matches, nothing is appended to `result` and the keyword vanishes. No warning, no exception.

Consequence: a typo in a stage prefix (`molases_duration=...`) means the parameter is silently ignored and the stage runs with its default. In an experimental timeline that is a physically wrong sequence which still executes.

**Fixed.** Unmatched keys are collected and raised together, each with the reason it could not be routed, alongside the stage names that were given. A keyword that named a real stage but not one of its parameters is reported against that stage, since a misspelled parameter is likelier than a misspelled stage.

The alternative — letting an unprefixed keyword broadcast to every stage — was rejected with #83; see fix direction (3) in §C.

### A2 — `cascade` uses substring matching, not prefix-anchored matching — **FIXED 2026-09-16**

The test is `if fname in k`, and the split is `k.split(fname, 1)[1]`. Correctness currently rests entirely on `sorted(f_names, key=len, reverse=True)`: `MOT_detuned_growth_duration` resolves correctly only because the longer name is tested first.

Two distinct hazards, worth keeping separate:

- **Stage named after another stage** (`MOT` / `MOT_detuned_growth`) — the genuine collision. If `MOT` itself had a parameter called `detuned_growth_duration`, the keyword `MOT_detuned_growth_duration` would be captured by the longer stage name and `MOT`'s parameter would be permanently unreachable.
- **Parameter merely containing a stage name** — harmless under prefix anchoring, hazardous under substring matching. Anchoring the match to the start of the key removes this class entirely.

**Fixed, both halves.** Matching is anchored with `k.startswith(fname + "_")`, which removes the "parameter merely containing a stage name" class entirely. Longest-first ordering is kept, because a shorter stage name can still legitimately prefix a longer one (`MOT_` also begins `MOT__detuned_growth_duration`), and the genuine collision is then settled by signature: a split is accepted only when the target declares the remainder as a parameter, or collects `**kwargs`. So if `MOT__detuned_growth` does not take the remainder but `MOT` does, the keyword reaches `MOT` — the case this entry described as permanently unreachable.

Signature checking only became safe once the operation layer stopped putting `**kwargs` on ordinary stages (§C, 2026-09-16): with every stage open, every split would have been accepted and the check would have bought nothing.

### A3 — `ramp` computes cleaned frames and then discards them

`timeline.ramp`. `new1_clean` and `new2_clean` are built by masking out degenerate rows (`mask__offending`), the emptiness of those cleaned frames gates an early `return timeline` — and then the function returns `wt_frame.concat([timeline, new1, new2])`, the *un*cleaned frames.

Net effect: the entire filtering block does nothing except occasionally trigger the early return. Degenerate rows (zero duration, or zero value change) reach `expand` and get expanded into pointless ramps.

Decide which behaviour is intended before changing anything — silently dropping a user's ramp is arguably worse than expanding a degenerate one. If dropping is right, return the cleaned frames. If not, remove the dead code and make the degenerate case raise.

**Verified 2026-09-02: the early return is not dead, and it silently discards whole ramps in the shipped demo.** The two branches behave differently, and both are wrong in different directions:

- *All* rows degenerate → both cleaned frames are empty → `return timeline`, and the entire ramp disappears without a word.
- *Some* rows degenerate → cleaned frames are non-empty → the **uncleaned** frames are returned, so every degenerate row survives to `expand`.

The first branch fires on a real composition. `cascade(demo.init, demo.MOT, demo.finish)` loses all seven analog variables from `finish`'s final ramp, because with the intermediate stages absent each one is already sitting at the value the ramp targets:

```
finalRamps variables, 3-stage cascade: ['⚓_002']              # the anchor only
finalRamps variables, full demo:       [7 coils/lockbox + '⚓_006']
```

The full demo is unaffected only because its intermediate stages move those values first. So the behaviour depends on which stages happen to be composed — a ramp that is present in one composition vanishes in another, with no diagnostic. That the `finalRamps` *context* still exists (the anchor creates it) makes it harder to notice.

Physically the dropped ramp is usually a flat line, so little is lost directly; the hazard is that its `duration` vanishes with it, so anything later placed relative to `"last"` rather than to an anchor shifts. Raising, rather than dropping, would surface the real condition: a ramp was requested to a value the variable already holds.

### A4 — `origin.auto` falls through to an implicit `None`, and `ramp` walks into it — **VERIFIED REACHABLE, highest severity**

`internal/origin.auto`. When `origin is None` and every entry in `origin__defaults` contains `"anchor"` but no anchor is available in the timeline, the loop `continue`s past every option and the function returns `None` implicitly.

Downstream, `origin=None` makes `find` return `[None, None]` and `update` return the timeline untouched — so the rows land at absolute time rather than relative to anything, without complaint.

**Verified 2026-09-01.** The guess that `config.ORIGIN__DEFAULTS` makes this unreachable is correct as far as it goes — its second entry `["last", None]` contains no `"anchor"`, so `auto` always returns it and never falls through. But `timeline.ramp` does not use the config default. It passes its own, single-entry, anchor-only `origin__defaults=[["anchor", "variable"]]`, for which the fall-through is the *only* other outcome. So the bug is reachable through the most heavily used function in the package, whenever the timeline it extends contains no anchor:

```python
base = tl.create(coil__A=0.0, t=5.0, context="stage1")
r = tl.ramp(timeline=base, coil__A=2.0, duration=1.0)
# ramp rows land at t = 0.0 -> 1.0, i.e. silently BEFORE the entry at t = 5.0
# with an anchor in `base`, the same call correctly gives t = 5.0 -> 6.0
```

This is the worst failure mode in the document: no exception, no warning, and the resulting sequence is not merely mistimed but *reordered* — the ramp precedes the state it was written to follow. It will run on hardware.

Note the interaction with the recommendation that every stage end with an `anchor` (see the paper, `sec:anchor`): following that convention masks the bug entirely, which is presumably why it has survived. It bites precisely the user who has not yet adopted the convention, or who ramps onto a bare `create`.

Fix direction: `auto` should not be able to return `None` implicitly. Either raise when no default applies — naming the timeline's lack of an anchor, since that is the actual cause — or fall back to `"last"` as the config default does. **Which of those two is right is an API decision**: raising is consistent with §"loud and early", falling back is consistent with `ORIGIN__DEFAULTS`. Do not choose unilaterally; see C1 for the analogous question.

**Addendum, 2026-09-03.** The same condition is handled two ways, worth fixing in one go: an *explicit* `origin="anchor"` on an anchorless timeline raises `anchor is an unsupported option for 'origin'` (verified), because `_to_col_var` falls through the variable and context lookups to its error branch. The *default* path, meeting the same absent anchor, is silent. Whichever is chosen — raise, or fall back with a warning — the two paths should agree.

### A5 — `stack` turns an unrecognised keyword into a phantom variable **[new, found 2026-09-02]**

`timeline.stack` forwards every keyword it is given to every constituent, which is the documented convenience for a shared `context`. But the core functions absorb unrecognised keywords into `**vtvc_dict`, where a keyword *is* a variable name. So a keyword that matches no parameter is not rejected — it becomes a row.

```python
tl.stack(base, tl.update(a__A=1.0), context="MOT", typo_duration=3.0)
#   time      variable  value context
#    0.0          a__A    1.0     MOT
#    0.0 typo_duration    3.0     MOT     <-- silently created
```

This is A1's sibling and strictly worse. Where `cascade` *drops* an unmatched keyword, `stack` acts on it: the parameter the user meant to set is silently ignored, *and* a phantom variable enters the timeline. It survives to export, where `connection.remove_unconnected_variables` quietly deletes it for having no connection — so nothing ever complains, and the run proceeds with the intended parameter unset.

Whether it stays silent depends on the origin machinery downstream. With `update` (whose default value-origin is `None`) it is silent, as above. With `ramp` the phantom variable reaches `origin.find` as a value origin and raises `"time_resolution is an unsupported option for 'origin'"` — loud, but blaming the wrong thing entirely; nothing in the message suggests a stray keyword.

Fix direction is A1's: validate keywords against the constituents' signatures and raise, listing the unmatched ones. See §C “Design intent”: this is layer 2, and the forwarding idiom does not use it. Note one implementation cost – `stack`'s constituents are opaque `lambda x, **kwargs__new` closures, so signature validation requires `function__lambda` to expose the function it wraps first. The two should be settled together, and C1 is the same decision a third time — `stack`, `cascade` and the core functions all inherit their permissiveness from `**kwargs` forwarding, and it is worth deciding the policy once rather than three times.

### A6 — an interwoven `ramp` silently loses its value origin and starts from zero **[new, found 2026-09-02; recalled by the maintainer as a long-standing design debate with T. W. Clark]**

`ramp` is the only core function that *needs* a value origin: a ramp runs from wherever the variable currently sits to the target, so the start value has to be looked up. That is why it does not use `config.ORIGIN__DEFAULTS` but passes its own `origin__defaults=[["anchor", "variable"]]` — time from the anchor, **value from the variable's own previous value**. `update` needs nothing of the kind, because its values are absolute.

The gap: `origin.auto` supplies that default **only when `origin is None`**, and an explicitly given origin replaces it wholesale rather than completing it. Worse, the user-facing shorthand for interweaving is a bare context name, and `ensure_iterable_with_None` pads a bare string to `[s, None]` — filling the time slot and nulling the value slot. So the documented interweaving idiom and ramp's value default are mutually exclusive:

```python
# coil__A = 2.0 at t=0 (stage1); 5.0 at t=1 (stage2); an anchor in each stage
tl.ramp(timeline=base, coil__A=9.0, duration=0.5)                          # 5.0 -> 9.0   correct
tl.ramp(timeline=base, coil__A=9.0, duration=0.5, origin="stage1")         # 0.0 -> 9.0   WRONG, silently
tl.ramp(timeline=base, coil__A=9.0, duration=0.5, origin=["stage1","variable"])  # 2.0 -> 9.0   correct
```

The middle line is `sec:interweaving` exactly as the paper teaches it, and it produces a ramp from **zero** rather than from the variable's actual value. On a coil that is a full-scale current swing at ramp speed; on a lockbox it is a full detuning sweep. Nothing warns.

Note that this is not a hole in the *design*: the paper (appendix, `sec:origin_full`) describes bounded value lookups precisely so that "an operation [can] be interwoven into the middle of an existing timeline and still see the state that physically precedes it", and the pair form `["stage1", "variable"]` does exactly that. The defect is that the shorthand cannot express it, and silently degrades instead of refusing.

Fix direction, and it is an API decision: **`auto` should complete a partial origin per slot rather than replace it wholesale.** A user-supplied `[str, None]` would take its value slot from the function's default — `None` for `update`, so nothing changes there; `"variable"` for `ramp`, so an explicit time origin keeps the value behaviour that makes a ramp a ramp. This changes the meaning of existing `ramp(..., origin=<str>)` calls, which is the point, but it must be a deliberate choice. **Settle B2 first or together**: the fix multiplies value-origin lookups, and B2 makes those order-dependent.

**Two claims in the manuscript are contradicted by this and must not be edited away** (§G — report, do not reconcile the prose):

- `sec:origin_full`: "No default in the package is value-relative; value origins are available … but are always requested explicitly." `ramp`'s start-point default `["anchor", "variable"]` *is* value-relative, and is the reason ramps chain correctly at all.
- The same appendix's account of interweaving is accurate for `update` but not reachable for `ramp` through the shorthand it documents.

### A7 — `"last"` and `"anchor"` are accepted as VALUE origins, where they are category errors **[new, found 2026-09-03]**

Both keywords are defined temporally: `"last"` means the highest time recorded so far, `"anchor"` the time of the most recent anchor. Yet `origin.find` resolves both slots of the pair through the same `_to_col_var`, so both are accepted in the *value* slot, silently, with no interpretation that makes physical sense.

Measured on a timeline with `coil__A` = 7.0 A, an anchor at t=5, and `shutter_MOT` = 1 at t=9:

```python
origin=[20.0, "variable"]  # -> 7.0   the variable's own last value   MEANINGFUL
origin=[20.0, "coil__A"]   # -> 7.0   same, named explicitly          MEANINGFUL
origin=[20.0, "anchor"]    # -> 0.0   the anchor row's dummy value
origin=[20.0, "last"]      # -> 1.0   shutter_MOT's state. In amps.
origin=[20.0, "prep"]      # -> 1.0   that context's last row, whatever variable it belongs to
```

`"last"` is the dangerous one: it returns the value of whichever variable happens to hold the highest time, so a digital line's 0/1 is added to a current in amps with no complaint. `"anchor"` is harmless only because anchors are created carrying value 0 — nothing enforces that, so it is a latent trap rather than a safe no-op. A context name in the value slot fails the same way.

It is not even consistently wrong, because the answer depends on which branch computes the lookup bound: `origin=["anchor", "last"]` gives 0.0, since the bound is the anchor's own instant and the anchor *is* the highest-time row there.

**What the manuscript actually says, and it splits this item in two** (`fig:origin` caption, `docs/paper/main.tex:916`): "With the exception of anchors, for which no value is defined, every option can serve as either a time or a value origin."

- **`"anchor"` in the value slot is a plain bug against the documented design.** The paper states no value is defined for anchors; the code silently returns the anchor row's dummy `0.0`. No design question — it should raise.
- **`"last"` and context names in the value slot are *licensed* by that caption.** So narrowing them is a change to the manuscript, not a bug fix, and belongs to the maintainer. The argument for narrowing is the measurement above: "every option can serve as either" is true mechanically but not physically, since the value it yields belongs to whichever variable happens to hold the highest time — a digital line's 0/1 added to a current in amps. My recommendation is to narrow and amend the caption, but it is a §G report, not a defect.

The figure's leaf wording already leans that way: `"last"` and `"anchor"` are described as *times* ("the highest time recorded so far", "the time of the most recent anchor"), while the value-capable leaves are described neutrally as *entities* ("entity of previously occuring variable").

Fix direction: split the vocabulary by slot. The time slot admits a number, `"anchor"`, `"last"`, `"variable"`, a variable name or a context name; the value slot admits a number, `"variable"` or a variable name, and **raises** on the rest. Raise rather than warn — unlike the time slot there is no sensible value to fall back to. Nothing is lost, because "the value `coil__A` held at the end of molasses" is already `["molasses", "variable"]`. See `docs/origin-resolution.md` for the full branch map.

### A8 — a value origin is added on top of an explicitly stated `ramp` start value **[new, found 2026-09-03]**

`ramp`'s value origin defaults to `"variable"`, and `_update_future` applies it **additively**. That is right for a variable whose start point was inferred, but it is applied just as readily to a start value the user stated explicitly in the 2-D input form.

```python
# coil__A last known at 7.0
tl.ramp(timeline=base, coil__A=[[0.0, 1.0], [0.5, 3.0]])
# start value comes out as 8.0 (= 1.0 + 7.0), not the 1.0 that was written
```

`tab:rampExamples` documents that exact form as "for cases where the start cannot be inferred from `origin`" — i.e. the user is overriding the inference — so adding the inferred value back on top defeats the only reason to use the form.

Fix direction: resolve the value origin only for variables in `df__no_start_points`, never for those in `df_1`. Settle together with B1 and A3, which sit in the same block of `ramp`.

### A9 — reserved origin words silently shadow real context and variable names **[new, found 2026-09-03]**

`_to_col_var` tests `"anchor"`, then `"last"`, then variable names, then context names. So a context or variable actually named `anchor`, `last` or `variable` is unreachable as an origin, silently. Verified with a context literally named `anchor` whose rows sit at t=1, alongside a real anchor at t=5: `origin="anchor"` resolves to **5.0**, not 1.0.

`_ORIGINS = ["anchor", "last", "variable"]` exists in `origin.py`, with a docstring saying these labels are reserved for interpretation by the package — and is referenced nowhere in it.

Fix direction: make `_ORIGINS` the single source of truth, and reject a context or variable name that shadows one at the point it is created. `connection.new` already validates variable names; contexts are unvalidated. A collision is a mistake in the client's vocabulary, so raising at creation beats resolving it silently either way.

### A10 — `create` silently corrupts a positional row of more than two elements — **GitHub issue #58, still open; verified 2026-09-09**

Reported by T. W. Clark on 2025-03-24 as "problem with `create` (varargs)", labelled `bug` and self-assigned. Confirmed OPEN via `gh issue view 58` on 2026-09-09 (superseding an earlier reading taken from a screenshot). Still reproduces verbatim.

```python
tl.create(AOM_imaging=[0.0, 0, "init"],                # kwargs -- correct
          AOM_imaging__V=[0.0, 2.0, "init"],
          AOM_repump=[0.0, 1, "init"])
#  time       variable  value context
#   0.0    AOM_imaging    0.0    init
#   0.0 AOM_imaging__V    2.0    init
#   0.0     AOM_repump    1.0    init

tl.create(["AOM_imaging", 0.0, 0, "init"],             # positional -- WRONG, silently
          ["AOM_imaging__V", 0.0, 2.0, "init"],
          ["AOM_repump", 0.0, 1, "init"])
#  time       variable  value context
#   0.0    AOM_imaging    0.0
#   0.0 AOM_imaging__V    0.0
#   0.0     AOM_repump    0.0
```

Every value collapses and every context is lost. No warning.

**Mechanism.** `internal/timeline/input.py`. `__find_depth` sees `vtvc[0]` as a collection and `vtvc[0][0]` as a string, so it reports depth 2. `__correct_variable_list` then builds `[[row[0], __ensure_time_context(row[1], ...)] for row in coll2D]` — it reads elements 0 and 1 and **discards `row[2:]` without comment**. `__ensure_time_context` treats `row[1]` as the *value*, taking the time from the `t=` default. So element [1] silently becomes the value and the stated time, value and context are all lost. Confirmed directly:

```python
wt_input.convert(["AOM_imaging", 0.0, 0, "init"], time=0.0)
# [['AOM_imaging', [[0.0, 0.0, '']]]]
```

Three-element rows fail identically. Only the two-element shapes parse correctly:

| row given | parsed as | |
| --- | --- | --- |
| `["a_x", 1.0]` | t=0.0, v=1.0 | correct, documented |
| `["a_x", [0.5, 1.0]]` | t=0.5, v=1.0 | correct, documented |
| `["a_x", 0.5, 1.0]` | t=0.0, **v=0.5** | wrong, silent |
| `["a_x", 0.5, 1.0, "ctx"]` | t=0.0, **v=0.5**, ctx=`''` | wrong, silent — the issue |

**Root cause is an ambiguity in the input grammar itself**, which is why no positional rule can be right: in a *list* row element [1] is a **value** (`[['variable', value]]`), while in the *flat* form it is a **time** (`variable, time, value, context`). Both are documented in `create`'s docstring. The meaning of element [1] therefore depends on the row's length, and `__correct_variable_list` simply picks one reading. See C5.

Strictly the reported shape is not among the documented forms — but it fails by corrupting data rather than raising, so by the priority rule at the head of this document it is a bug either way.

**There is a commented-out test for exactly this**, `test/wigner/time/timeline/test_timeline_create.py:108`, sitting between two working cases:

```python
tl.create(AOM_repump=[10.0, 0.0, "important"], timeline=df_previous),
tl.create("AOM_repump", 10.0, 0.0, "important", timeline=df_previous),
# tl.create(["AOM_repump", 10.0, 0.0, "important"], timeline=df_previous),   <-- commented out
tl.create(["AOM_repump", [10.0, 0.0, "important"]], timeline=df_previous),
```

So the case was hit, parked, and never returned to — which is why the suite is green.

Note that `internal/timeline/input.py` is byte-identical on `main` and every working branch, so this affects the released state and development alike.

Fix direction, and it is C5's decision: either read a row of more than two elements as `[variable, time, value, context]`, mirroring the flat form — which also makes the three-element case unambiguous — or reject it loudly. Doing both is best: support the three- and four-element rows, raise on anything still unmatched, and uncomment line 108. Note that supporting it changes what `["a_x", 0.5, 1.0]` means, from v=0.5 to t=0.5; that is technically breaking, though only for behaviour that is currently wrong and undocumented.

---

## B. Correctness

### B1 — `ramp`'s degenerate-row check aligns on index, not on variable — **misalignment VERIFIED; cartesian-expansion sub-claim withdrawn**

`np.abs(new1["time"] - new2["time"])` relies on pandas index alignment. `new1` is `concat([df_1, df__no_start_points])` and `new2` is `df_2`; there is no guarantee that position *i* in one refers to the same variable as position *i* in the other, particularly in the `max_ndim == 2` branch where the two frames are built from different subsets of `vtvc_dict`.

**Verified 2026-09-01.** Reproduced with mixed 1-D/2-D input, which is exactly the `max_ndim == 2` branch:

```python
base = tl.stack(tl.create(a_x__V=0.0, b_y__V=0.0, t=0.0, context="s"), tl.anchor(0.0))
tl.ramp(timeline=base, a_x__V=1.0, b_y__V=[[0.5, 0.0], [0.5, 3.0]], duration=1.0)
# new1 rows come out ordered [b_y, a_x];  new2 rows [a_x, b_y]
```

The orders differ deterministically, not by accident: `df_1` is built from `_vtvc_2d_0` (the 2-D variables only) with the 1-D variables appended afterwards as `df__no_start_points`, while `df_2` is built from `_vtvc_1d | _vtvc_2d_1` — dict union, so 1-D first. Any mix of 1-D and 2-D variables in one `ramp` call therefore compares one variable's time and value against another's.

The consequence is currently masked by A3: `mask__offending` is computed and then discarded, so a wrong mask changes nothing except which calls hit the early `return timeline`. Fixing A3 without fixing B1 would activate this.

**The second paragraph of the original entry does not hold and has been withdrawn.** Duplicate index labels do not arise: `new1` receives a fresh `RangeIndex` from `wt_frame.concat`, whose `ignore_index` defaults to `True`, and `new2` a fresh one from the frame it is built from. Labels are unique on both sides, so the subtraction stays elementwise and no cartesian expansion occurs. The fix direction below is unaffected.

Fix direction: match on `variable` explicitly (merge or set the index to `variable`) rather than relying on positional alignment.

### B2 — `find_every_origin` is order-dependent

`internal/origin.update`. Inside the per-variable loop, `time__max__relative=timeline__future["time"].min()` is recomputed on each iteration — but `_update_future` mutates `timeline__future` in place, so earlier iterations shift the times that later iterations measure against. The result therefore depends on the iteration order of `timeline__future["variable"].unique()`, which is insertion order, which is user-input order.

Also note the function reassigns `timeline__future` locally and returns nothing; the caller relies on in-place mutation through the shared object. It works, but the rebinding is misleading — either return the frame and use the return value, or drop the rebinding.

**Verified 2026-09-01** (by inspection). Both halves are as described. `time__max__relative` is consumed only by `find`'s *value*-origin branches (`[None|float, str]` and `[str, str]`), so the order dependence needs a value origin to be in play.

**Correction, 2026-09-02: this is live, not latent, and it is observable.** The earlier note here said no package default is value-relative so an explicit one was needed. That is wrong — `ramp` passes `origin__defaults=[["anchor", "variable"]]` (see A6), so *every* multi-variable `ramp` is resolving value origins by default. Reproduced: adding an **unrelated** variable to the same `ramp` call changes another variable's resolved start value.

```python
# b__A steps 10 -> 20 across the anchor at t=5
tl.ramp(timeline=base, duration=1.0, b__A=[[0.5, 0.0], [0.5, 3.0]])
#   -> b__A starts at 20.0
tl.ramp(timeline=base, duration=1.0, b__A=[[0.5, 0.0], [0.5, 3.0]], a__A=1.0)
#   -> b__A starts at 10.0
```

Because the bound is recomputed as `timeline__future["time"].min()` inside the loop while `_update_future` mutates those times, which past value counts as "in effect" depends on what else is being ramped and in what order. The effect needs heterogeneous start times among the ramped variables — i.e. the `max_ndim == 2` branch, the same branch B1 mishandles — so a test written with uniform 1-D input will pass vacuously. Fix as below (hoist the minimum out of the loop); doing so also removes the coupling between B1's row ordering and this value resolution.

Fix direction: compute the minimum once, before the loop.

### B3 — `previous` sorts a filtered slice in place

`internal/origin.previous`. `tl__filtered` is a boolean-mask slice of `tline`; `tl__filtered.sort_values(sort_by, inplace=True)` on such a slice is unreliable under copy-on-write and may either warn, no-op, or write through to the parent depending on pandas version. pandas 3.x makes CoW unconditional.

**Verified 2026-09-01** (by inspection). Present as described. Reachable only through the public `timeline.previous(sort_by=...)`: `origin.find` calls `previous` without `sort_by`, so the whole `sort_values` branch is dead on the internal path. That caps today's severity, and also means it will not be caught by any test that goes through `origin`.

Fix direction: `tl__filtered = tl__filtered.sort_values(sort_by)`.

### B4 — `ramp` writes through a slice

`df__no_start_points = df_2[~df_2["variable"].isin(df_1["variable"])]` is a view-or-copy, and the following `.loc[:, ["time", "value"]] = 0.0` assigns into it. Same CoW exposure as B3.

**Verified 2026-09-01** (by inspection). Present as described, but note the failure mode differs from B3's and is milder: the assignment is *intended* to modify only the local frame, which is what is passed to `concat` downstream, so writing to a copy is what the code actually wants. The exposure is a `SettingWithCopyWarning` and a dependence on pandas' copy-or-view decision, not wrong data. No such warning is emitted by the current suite on pandas 2.2. Still worth fixing — the guarantee is not one to rely on across a pandas major version — but it does not belong above B3.

Fix direction: `.copy()` at construction.

### B5 — `expand` mutates the caller's dataframe

`timeline.expand` calls `timeline.drop(index=..., inplace=True)` and `timeline.drop(columns=["function"], inplace=True)` on the argument. Every other main function in this module is non-mutating and returns a new frame; `expand` breaks that contract, so a caller who keeps a reference to the pre-expansion timeline finds it corrupted.

This matters more than it looks: the "timeline as inspectable data" story depends on frames not changing under you.

Fix direction: operate on a copy.

### B6 — `expand` assumes exactly `num__bounds` rows per group

`_pt_start, _pt_end = _group[["time", "value"]].values` unpacks assuming two rows. Groups are formed by `_dff.index // num__bounds` after a reset, so an odd total row count leaves a final group of one and the unpack raises a bare `ValueError` with no indication of which variable is malformed.

Fix direction: check group size explicitly and raise naming the offending variable. This becomes load-bearing if `num__bounds != 2` is ever implemented.

### B7 — a value-only origin against a variable raises a raw `TypeError` **[new, found 2026-09-03]**

In `find`'s `[None | float, str]` branch the value lookup's bound is `n1 + time__max__relative`. When the time slot is `None` — the caller asked for a value origin and no time origin — that is `None + float`:

```python
tl.update(timeline=base, coil__A=0.0, t=3.0, origin=[None, "variable"])
# TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'
tl.update(timeline=base, coil__A=0.0, t=3.0, origin=[None, "coil__A"])
# TypeError: the same
tl.update(timeline=base, coil__A=0.0, t=3.0, origin=[None, 2.0])
# fine -- numeric value origins work
```

So a value origin resolved against a variable is unusable through the public API unless a numeric or string time origin is supplied too. The `[str, str]` branch does not have the bug, because there the bound is built from the *resolved* time.

A related rough edge in the same expression: when the bound is small enough to exclude every past row, the error is `Previous <var> not found`, naming neither the bound nor the instant that produced it. The refusal is arguably correct — the value in effect at an instant before the variable existed does not exist — but it is undiagnosable as written, and under a "value default is 0" policy the better answer may be 0 with a warning.

Fix direction: give both branches one definition of the bound, namely the instant the new rows will occupy once the time origin is applied. That removes the `None` arithmetic and makes the branches agree. Do it together with B2, which is in the same expression.

### B8 — `"last"` on an empty timeline raises an opaque pandas error **[new, found 2026-09-03]**

`origin="last"` resolves through `previous` to `dataframe.row_from_max_column`, which is `df.loc[df[column][::-1].idxmax()]`. On an empty frame that is `ValueError: attempt to get argmax of an empty sequence`, with nothing to connect it to origins, timelines, or the user's call.

It is reachable through the documented default, since `config.ORIGIN__DEFAULTS` falls back to `"last"` — so `update` on an empty timeline takes this path. This is the hole that a terminal `0.0` step in the default chain would close (`docs/origin-resolution.md`, suggested semantics item 3).

Fix direction: guard in `previous`, and either raise naming the timeline as empty or fall back to 0.0 with a warning, consistent with whatever the default chain decides.

---

## C. Open API decisions — do not settle unilaterally

These are design questions, not bugs. Flag and ask rather than choosing.

### Design intent — keyword forwarding is a feature, not an accident **[stated by the maintainer and validated 2026-09-02]**

`**kwargs` forwarding down a composition is deliberate and load-bearing. The intent: `default_state` is written **once**, describing the apparatus' base state, and any additional variable initialisation can be injected into it from anywhere higher in the composition. A keyword that no intermediate stage consumes is *meant* to fall through and land in `default_state`'s terminal `create`/`update` call, where it becomes a variable-value pair.

Validated end to end:

```python
tl.cascade(demo.init, demo.MOT, init_coil_MOTlower__A=0.5, MOT_duration=1.0)
# -> coil_MOTlower__A = 0.5 in the ADwin_LowInit context
```

`cascade` routes `init_*` to `init`, which forwards to `default_state`, which expands `**kwargs` into `tl.create(...)`, where the unrecognised keyword is correctly read as a variable name.

**The consequence for A1, A2, A5 and C1: three layers are involved and only one of them must stay permissive.**

1. `cascade` — routes by *function-name prefix*. Validation here asks "does this keyword begin with a known stage name?", which needs no signature inspection and does not touch the idiom. **Can be made strict.**
2. `stack` — forwards every keyword to every constituent. Verified 2026-09-02 that the idiom does *not* use this path: every `**kwargs` expansion in `demo/full_experiment.py` (8 sites) goes into a *direct* call to a core function or helper, while `stack`'s own keywords are exclusively `context=` (5 sites). **Can be made strict without breaking the demo.**
3. The core functions' `**vtvc_dict` — an **open namespace by design**; this is where the intent terminates and where a keyword legitimately becomes a variable. **Must stay permissive.** Signature-strictness here would destroy the feature.

C1 as originally posed conflates 1 and 3, which is why it looked like an all-or-nothing choice. It is not.

**Layer 2b — the operation layer's own stages — was narrowed on 2026-09-16** (`19d41ad`, lab `36f7fdf`). `**kwargs` now appears on `default_state` and on the two functions that wrap it, `init` and `finish`, and nowhere else in the demo or the lab. Every other stage declares what it forwards: `timeline=None`, plus `t` and `context` for `pull_coils`, the only stage another stage calls. The diagnostics functions keep the `origin` and `context` they already declared and gain `timeline=None`.

This is the decision recorded below as "event functions lose `**kwargs`", and it is the prerequisite C1 was waiting on: with stages carrying declared parameters, `cascade` can accept a keyword split only when the remainder is a parameter the target actually takes, and `default_state`/`init`/`finish` stay correctly permissive because they still have `**kwargs`. The policy is therefore *derived* from `inspect.signature` rather than configured.

Two findings from doing it:

- `context` does **not** belong on every stage. Across the demo and the lab there are exactly two stage-calls-a-stage sites, and both are `pull_coils`. Everything else sets its context on its own `stack` or passes it straight to the core call.
- `origin` should **not** be added uniformly, and the existing code already drew the line correctly. It belongs on a stage meant to be *placed* — the interwoven diagnostics, every one of which declares it — and not on a stage forming a causal link, where it would exist only to be given wrongly. The signature therefore says which kind a stage is. Recorded in the manuscript at `sec:interweaving`.

The other half of the decision — `finish` deriving the final state from the timeline rather than from a hardcoded list — has **not** landed, and is still fix direction (1) below.

**The intent is only half-served: injection reaches one end of the experiment, not both.** The point of `default_state` is that an injected variable is *both* an initial and a final condition — two rows, one per special context. `cascade` cannot express that: its dispatch loop `break`s on the first matching stage name, so each keyword is routed to exactly one stage.

```python
cascade(init, MOT, finish, init_test__V=1.0)                        # -> ADwin_LowInit only
cascade(init, MOT, finish, finish_test__V=1.0)                      # -> ADwin_Finish only
cascade(init, MOT, finish, init_test__V=1.0, finish_test__V=1.0)    # -> both. The only way.
cascade(init, MOT, finish, test__V=1.0)                             # -> dropped entirely (A1)
```

Requiring the keyword twice is not a cosmetic problem: it reintroduces precisely the failure the paper cites as the motivation for `default_state`. From `sec:discussion` — the apparatus' default state "is required both before a run and after it, and in our previous implementation it was written twice, in the initialization and finalization sections, from which the two copies had quietly diverged – disagreeing on several shutters and omitting others altogether." `default_state` removed that duplication from the *stage bodies*, and keyword routing has reintroduced it at the *call site*. Forget one of the two prefixes and the apparatus ends a run in a different state from the one it started in, silently.

**There is no funnel: an unconsumed keyword lands at whichever `**kwargs` sink is lexically nearest, and only `init` and `finish` have `default_state` as theirs.** Surveyed empirically 2026-09-02, each stage probed on a realistic base built from its predecessors:

| stage | its `**kwargs` sink | an unconsumed keyword becomes |
|---|---|---|
| `init` | `default_state` → `tl.create` | 1 row, `ADwin_LowInit` — the intended behaviour |
| `finish` | `default_state` → `tl.update` | 1 row, `ADwin_Finish` — the intended behaviour |
| `MOT` | `tl.update` | 1 row in the `MOT` context: a step mid-experiment, silently |
| `MOT__detuned_growth` | `tl.ramp` | `ValueError: <var> is an unsupported option for 'origin'` if the variable is not already in the timeline; otherwise a 2-row ramp from its current value, in that stage's context |
| `molasses` | `tl.ramp` | as above |
| `optical_pumping` | `tl.ramp` | as above |
| `magnetic_trapping` | `pull_coils` → `tl.ramp` | as above |

So the same keyword is a default-state initialisation at one end, a mid-experiment step in `MOT`, and either a hard error or a ramp in the four ramp-based stages. The failure modes are inconsistent in kind, not just in destination.

**Using `stack` instead of `cascade` does not help; it is strictly worse.** A keyword in `stack`'s own scope cannot reach any stage's `**kwargs`, for two independent reasons:

1. The stage functions are evaluated *before* `stack` receives them — `stack(init(), MOT(), …)` has already called `init()` — so stack's keywords can only reach the deferred objects they returned, never the stage signatures.
2. Forwarding into a *composed* stage raises. `stack`'s callable branch wraps its first constituent as `lambda x: timeline_or_f(x, **kws)`, with no `**kwargs` of its own, so a keyword forwarded into it fails: `TypeError: stack.<locals>.<lambda>() got an unexpected keyword argument`. A *primitive* deferred constituent (`tl.update(…)`) accepts it instead and turns it into a phantom variable — A5. Which of the two happens depends on whether the constituent was built by `stack` or by a core function, an implementation detail invisible at the call site.

**One mechanism already does what is wanted, but cannot currently be used for it.** `cascade` keys its argument map by `f.__name__` and looks it up once per occurrence, so a stage appearing twice receives the same keywords both times:

```python
tl.cascade(start, marker, middle, marker, marker_probe__V=1.0)
#   probe__V = 1.0 in `marker` at t=0.0   <-- both occurrences
#   probe__V = 1.0 in `marker` at t=1.0
```

That is exactly the two-rows-at-both-ends semantics. It cannot be applied to `init`/`finish` as they stand, because the two ends need *different* fixed arguments — `f=tl.create` against `f=tl.update`, and different contexts — and same-named stages are forced to receive identical keywords. Worth noting as a side effect regardless: two stages sharing a `__name__` silently share parameters, and `functools.partial` cannot be used to distinguish them because `cascade` reads `__name__`.

Two further gaps in the same area:

- **An injected analog variable is stepped, not ramped.** `finish` ramps a hardcoded list of seven analog variables; an injected one is absent from it, so it gets a bare `update` in `ADwin_Finish` and jumps rather than ramping. This is the standing TODO in `finish` ("The default_state function should be used to populate the ramp?"), and the injection feature is what makes it matter.
- **`functools.partial` cannot be used to bind the injection once**, which is the obvious workaround: `cascade` routes on `f.__name__`, which a `partial` object does not have, so `cascade(partial(init, x=1), ...)` raises `AttributeError`. Any fix that expects users to pre-bind stages needs `cascade` to fall back to `func.__name__` for partials.

Fix directions, cheapest first. (1) Keep routing as it is and have `finish` *derive* the final state from the timeline instead of from keywords — the rows already sitting in the `ADwin_LowInit` context are the initial state, so `finish` can mirror them, ramping the analog ones and stepping the digital. This needs no library change, is pure operation layer, makes divergence structurally impossible rather than merely discouraged, and settles the ramp TODO at the same time. It is also the data-oriented answer: the state is already in the timeline as data, so read it rather than re-declaring it. (2) Give `cascade` explicit multi-target routing. (3) Make un-prefixed keywords broadcast — rejected: they would reach every stage, and every stage would turn them into rows. Note that (3) is also in direct tension with A1's fix, since A1 proposes raising on exactly the un-prefixed keyword that (3) would give meaning to; settle A1 and this together.

**Known limit of the idiom.** Injection can *add* a variable but cannot *override* one that `default_state` already names explicitly:

```python
tl.cascade(demo.init, demo.MOT, init_shutter_science=1)
# TypeError: create() got multiple values for keyword argument 'shutter_science'
```

Loud, so not dangerous, but it blocks the natural use of varying one element of the default state for a single run. Worth deciding whether `default_state` should merge rather than collide — e.g. by holding its defaults in a dict and doing `{**defaults, **kwargs}` — which would make the override work and cost nothing elsewhere.

### Decision — narrow the open namespace to one stage **[maintainer, 2026-09-02]**

`**kwargs` forwarding is superfluous for the *event* functions and will be removed from them. It remains only in `default_state`, reachable via `init`. `finish` will replicate the initial state from the timeline plus ramps, rather than receiving it through keywords.

Consequences for the routing items, each checked against a model of the proposed shape:

| item | effect |
|---|---|
| **A2** (substring mis-routing) | **Severity collapses from silent to loud.** With no `**kwargs` on the wrong stage, Python rejects the bad remainder itself: the `science` case becomes `TypeError: science() got an unexpected keyword argument ''`, and a typo becomes `TypeError: MOT() got an unexpected keyword argument 'typo__A'`. Prefix anchoring is still worth its one line, but this stops being a silent-failure item. |
| **A1** (unmatched keyword dropped) | **Unaffected. Still needs the library fix, and becomes the only remaining silent hole in the chain.** `cascade` discards a keyword matching no stage name *before* calling anything, so Python never gets the chance to object. Verified: `probe__V=1.0` still vanishes without trace. |
| **A5** (`stack` phantom variable) | **Unaffected, and orthogonal.** `stack` forwards to the deferred core-function object, never through a stage signature, so the phantom is created at the `**vtvc_dict` layer. The export-time warning (A5 option b) remains the right instrument. |
| **C1** | **Becomes answerable and nearly free** — see below. |

The reason this helps C1 so much: its stated cost was that strictness "breaks `**kwargs`-forwarding stages, of which the lab example has several". After this change the lab example has exactly **one**. More importantly the policy no longer needs to be *chosen*, because it can be *derived* — `inspect.signature` reports whether a target has a `VAR_KEYWORD` parameter:

- target has `**kwargs` (i.e. `init`) → the remainder is free, and is a variable name;
- target has an explicit signature → the remainder must be a declared parameter, else raise.

This rule is a property of the target, not a configuration flag, so it is safe for arbitrary client code — a user who keeps `**kwargs` on their own stages simply keeps the permissive behaviour there. The demo cleanup is what makes the lab benefit from it.

It also rescues A2's proposed tie-break. While every stage had `**kwargs`, "is the remainder a real parameter?" was always trivially true and therefore useless as a discriminator for ambiguous splits. With six of seven stages explicit, it discriminates.

**One asymmetry `finish` must preserve.** It is not a pure mirror of `init`: `MOT_ON` defaults to `False` at `init` and `True` at `finish` — the MOT shutters are deliberately closed at the start and open at the end. (The shipped cascade sets both `True`, so they agree today, but the differing defaults record the intent.) So the derivation should be "mirror the `ADwin_LowInit` rows, then apply named overrides", not a bare copy. Deriving also settles the ramp TODO: `finish` can ramp exactly the analog variables it finds among those rows, so an injected analog variable is ramped rather than stepped.

### C1 — Should `cascade`'s signature checking default to strict? — **RESOLVED AND FIXED 2026-09-16 (yes, and derived rather than configured)**

The question was whether strictness should be a setting. It should not, because once the operation layer confines `**kwargs` to `default_state` and the two functions wrapping it (§C, same day), the policy follows from the target's signature: a split is accepted when the target declares the parameter, **or** when it collects `**kwargs` and is therefore deliberately open. `init` and `finish` stay permissive for exactly the reason `sec:forwarding` wants them to, and every ordinary stage is closed, without either being configured.

That ordering mattered. Signature checking before the `**kwargs` narrowing would have bought nothing at all — with every stage open, every split would have been accepted.

Fixes A1 and A2 together, and removes the cascade half of A5. Verified that the demo's own 20-keyword `cascade` still routes, that injection through `init` into `default_state` still works, and that both error kinds report usefully:

```
`cascade` could not route 1 keyword(s):
  MOT_duratoin -> `duratoin` is not a parameter of `MOT`
```

### C2 — Should `create` accept origin parameters? — **RESOLVED AND FIXED 2026-09-16 (no), with #45**

`create` passed `origin` straight to `wt_origin.update` while `update` routed through `wt_origin.auto`. The asymmetry was deliberate in the first sense offered: `create` starts a timeline, so it has nothing to be relative to.

**Settled by deciding it takes neither `origin` nor `timeline`**, which is also what the manuscript has documented all along — `sec:functions` gives the signature as `def create( *vtvc, t=0.0, context=None, **vtvc_dict )`, with no `timeline`, no `origin` and no `schema`. The code was the thing out of step, so this is a D7 reconciliation that needs no manuscript change.

The shared argument-resolution machinery moved to an internal `_populate_timeline`, which both public functions call; see #45. Nothing is lost: a numeric `origin` on a timeline-less `create` only offset `t` and the value, which is arithmetic the caller can do, and no call site anywhere used it. A string origin already raised.

One subtlety worth recording, because it defeats the obvious implementation. Removing the parameters from the signature is not enough: `**vtvc_dict` is an *open namespace*, so `timeline=` and `origin=` fall into it and are then re-bound by `_populate_timeline`, which does declare them — silently reinstating the arguments the signature exists to withhold. `create` therefore intercepts both names explicitly and raises, pointing at `update`. Neither is a valid `variable` name under `config.VARIABLE__REGEX`, so the interception cannot shadow a legitimate one.

### C3 — `anchor` with `t=None`

The docstring carries an unresolved TODO asking what happens if `t` is unspecified, with the author's own guess that it fails. Establish the intended behaviour and either give `t` a meaningful default or reject `None` explicitly.

### C4 — the `timeline` argument's full contract — **RESOLVED AND PARTLY FIXED 2026-09-16**

**The broadening is done.** `util.ensure_not_deferred` is now `util.ensure_timeline`, and the contract is three-way rather than one-and-a-half:

| `timeline` is | behaviour |
| --- | --- |
| a `wt_frame.CLASS` | evaluate, return a timeline |
| `None` | defer, return a function |
| callable | `TypeError` — the nesting message, unchanged |
| anything else | `TypeError` naming the function, the argument and the type |

A list, a string, an int or a dict used to fail far downstream on whatever dataframe attribute was touched first, naming neither the function nor the argument.

**The composition branch was considered and rejected** (maintainer, 2026-09-16). Letting `timeline=<callable>` compose rather than raise looked like a natural fourth row, and is not:

1. *It converts D17 into a feature.* Three different things are callable — a deferred core call, a composed `stack`, and an **uncalled user stage** — and they are indistinguishable by type or signature. A single "callable → compose" row routes all three to composition, which for the third means binding the timeline to the stage's first parameter. The branch would have removed the only guard that currently catches D17.
2. *It widens an inconsistency §C already records.* There are two ways a composed callable gets built and they behave differently under `stack`'s keyword forwarding — "an implementation detail invisible at the call site". Nesting would add a third before the existing two are reconciled.
3. *It re-legitimises the form `stack` exists to replace.* `main.tex:702` introduces `stack` precisely by contrast with `ramp(..., timeline=update(..., timeline=timeline))`. Nesting reads inside-out; `stack` reads top-to-bottom. Supporting both gives two idioms for one thing, and the newly-supported one is the less legible.

If it is ever wanted, the prerequisite is now in place: D17's tagging splits "callable" into *tagged deferred* (compose) and *any other callable* (error), so the row would no longer be a guess. It should be chosen on its merits, not inherited from loosening a guard.

### C5 — settle and document the whole `*vtvc` / `**vtvc_dict` input grammar **[maintainer, 2026-09-09]**

The input grammar is the most-used part of the public API and the least specified. `create`'s docstring lists five forms; `tab:inputSpecs` in the paper lists five *recommended* ones, all keyword-based, and defers the rest to "more foundational forms ... for programmatic use; see the API documentation" — which does not currently document them. A10 is what that gap costs.

Two things are wanted, in this order.

**1. Decide the grammar, then enumerate it.** Deciding comes first because the grammar is genuinely ambiguous today, not merely undocumented: element [1] of a list row is a *value*, while the second positional argument of the flat form is a *time*. Any enumeration has to resolve that before it can be written down. Questions that need answers:

- Is a row of more than two elements `[variable, time, value, context]` (A10)?
- Is a bare `[]` meaningful? A tuple rather than a list? Both are currently accepted silently.
- What is the maximum nesting, and what happens past it? `__find_depth` raises "input involves too deeply nested array" at depth 4 but says nothing about which argument.
- Do `t=` and `context=` act as defaults, as overrides, or as errors when a row also states them?

**2. Then document it in `create`'s docstring**, so it reaches the generated API pages (`docs/api.md` renders `::: wignertime` through mkdocstrings, so a docstring is the only place this will publish from). The docstring already carries a TODO asking for exactly this: "document the possible combinations of arguments ordered according to usecases". A table of shape against meaning, with one worked example each, is the right form — the paper's `tab:inputSpecs` is the model, extended to the positional forms.

**3. Weed out the silent failures while enumerating.** This is the part that matters most, and the enumeration is the natural occasion for it: every shape that the grammar does *not* accept should raise, naming the argument and the shape received. Today the unsupported shapes are absorbed. Known so far, all of them silent: A10 (rows longer than two elements), and `[]` and tuples accepted without comment. One further oddity for the enumeration to settle rather than a defect: `__ensure_time_context`'s `case 1` branch reads `row[1]` as a context when `context` is falsy, but `case 1` is entered only when rows are one element long, so that arm needs ragged input to fire and may simply be dead. Checked 2026-09-09 that it causes no observable difference — `context=""` and `context=None` both yield `''` — so it is a question of intent, not a bug.

A property-based test would suit this better than more `parametrize` cases: generate shapes, assert that each either produces the documented frame or raises, and that nothing lands in between. That is the check that would have caught A10 in March 2025.

Related: D10 (the `ensure_pair` typo and double normalisation) is in the same input-handling area; C4 governs the `timeline` argument rather than the vtvc arguments, but the same "accept, compose, defer, or raise" discipline applies.

---

## D. Structural

### D1 — `origin.py` module identity — **RESOLVED AND FIXED 2026-09-01**

The snapshot of `internal/origin.py` imports `wignertime.internal.origin as wt_origin` and calls `wt_origin.find(...)` inside `update`, while also defining a module-level `find`. This is either a module importing itself, a public shim mistaken for the internal module, or genuine duplication.

**Finding: the first of the three. A module importing itself.** There is exactly one `origin.py` in `src/` (`src/wignertime/internal/origin.py`); there is no public shim and no duplication. The self-import is legal — the module object is already in `sys.modules` by the time the statement executes — and `wt_origin.find` resolved to the same function object as the module-level `find`. So the module map is the obvious one, and no inference elsewhere in this document was corrupted by it.

**Fixed.** The self-import was removed and the two call sites changed to the plain local `find`. Three lines; suite unchanged at 193 passed. Nothing else in the origins code was touched.

### D2 — `timeline.previous` is a deprecated duplicate

Marked DEPRECATED in its own docstring; delegates to `wt_origin.previous`. The comment asks whether it should be deleted in favour of the internal implementation. Decide as part of settling the public API surface, not ad hoc.

### D3 — Mutable default argument

`ramp(..., origin2=["variable"])`. Not mutated in the current body, so harmless today, but it is a latent trap.

### D4 — Incorrect variadic annotations

`stack(timeline_or_f, *fs: list[Callable], ...)` and `cascade(*fs: list[Callable], ...)` annotate each individual argument as a *list* of callables. Should be `*fs: Callable`.

### D5 — `context_info` pandas coupling

Carries a TODO to remove the pandas dependence. Relevant to the polars-backed path; not urgent.

### D6 — `national_instruments/__init__.py` does not parse **[new, found 2026-09-01]**

`src/wignertime/national_instruments/__init__.py` has a missing comma between the message and `UserWarning` in its `warnings.warn(...)` call. The module is a syntax error: `import wignertime.national_instruments` raises `SyntaxError`, and `black` cannot format the file (it is the one "cannot format" entry in a whole-repo run).

Nothing imports it, which is why the suite never noticed. But it ships in the wheel, so `pip install wigner-time` delivers a package containing an unimportable module — and the module's whole purpose is to greet an NI user with a polite "not implemented" message, which it cannot currently do.

One-character fix, no design question. Left unfixed only because it fell outside the scope of the 2026-09-01 pass.

### D7 — Reconcile all code to the paper version **[maintainer decision, 2026-09-02]**

`docs/paper/main.tex` is canonical. Where the code and the manuscript disagree, **the code changes.** This is the same direction as §G: the manuscript is not to be edited to match the code.

**Scope to settle before starting.** The paper fixes the naming of everything it *shows*; for library internals it never shows there is no paper version to reconcile to, so those are out of scope by construction. Proposed reading: reconcile the public API surface, the demo, and the ADbasic listing; leave internal identifiers (`num__bounds`, `column__value`, `timeline__past`, `mask__changed`) alone. Confirm this before renaming anything, because the alternative reading — that the paper's single-underscore style governs internals too — is a very large change.

Do not conflate the two naming systems:

- **Variable names** — `<device>_<UID>(__<unit>)`, enforced by `config.VARIABLE__REGEX` and by `connection.new`. Paper and package agree; the system is load-bearing. **Settled differently from what this entry first assumed, 2026-09-11/12** — see the lab-code paragraph below. The convention is a *default*, as `main.tex:428` already says ("the package *by default* assumes and enforces … Any alternative convention should be applied consistently"), so it now lives in `config` and is read at call time rather than being a constant in `variable`.
- **Python identifiers** — stage parameters and keyword names. The package uses `__` as a qualifier separator, the paper's listings use a single `_`. This is where the divergence lives.

Known divergences, as an inventory rather than a plan:

*Shipped demo (`src/wignertime/demo/full_experiment.py`) against `sec:demonstration`.* Parameter style throughout (`duration__coil_ramp` / `duration_coil_ramp`, `lag__MOTshutter` / `lag_MOT_shutter`, `li`,`ui` / `lower_current_initial`,`upper_current_initial`, `toMHz` / `to__MHz`); `shutter_OP001`,`shutter_OP002` / `shutter_OP1`,`shutter_OP2`; `MOT__detuned_growth` / `MOT_detuned_growth`; `pull_coils(duration, l, u, lp, up, pt)` / `pull_coils(duration, lower_current, upper_current, pt)`; the paper has a `MOT_off` stage and a `delay_shutter_reinitialization` parameter that the code inlines as `0.1`; the paper's `magnetic_trapping` gives `context` to `anchor` rather than to `stack`; `wtf.save` / `wtfile.save`.

*Real lab code (`experiment.py`, `diagnostics.py`) against the current package.* **Largely resolved 2026-09-11/12**; both repositories were changed, in opposite directions.

The port itself is done (lab commits `dd08fce`, `62a400f`): `con.connection(...)` → `adcon.new(...)`; `devices` from a raw `unit_range`/`safety_range` frame to `device.new(...)` with `to_V`/`value__min`/`value__max`; `ad.core.to_data` + `initialize_ADwin` → `adwin.core.create`; `conversion.unit_to_digits` → `conversion.to_digits`. `internal/timeline/validate.py` is now the only thing left expecting the old schema (see the note on that module in `CLAUDE.md`).

**The "live bug" this entry recorded is gone, and was never fixed by us.** It claimed the stage functions wrote `coil_MOT_lower__A` etc. while the connection table declared `coil_MOTlower__A` etc., so the join in `adwin.internal.add` would miss and `remove_unconnected_variables` would silently drop all five. That was true of the snapshot audited on 2026-09-02, but the lab's own rename (`ee683d9`, `a499c79`, `a631f2a`) had already brought the table into line. Verified 2026-09-11 by differencing the set of declared names against the set of written names: both differences are empty.

**The `variable.REGEX` violations were resolved by changing the package, not the lab** (maintainer decision, 2026-09-11; Wigner Time commit `5b648d1`). The lab keeps snake_case, so `<UID>` may now contain single underscores and `coil_MOT_lower_plus__A`, `shutter_transverse_pump` and `AOM_OP_aux` validate. `__` is still the unit separator and may appear at most once, at the end, so `shutter__repump` and `coil_MOT__lower__A` are still rejected. Of the names this entry listed, only `dispenser__A` remained invalid — it has no `<UID>` at all — and the lab renamed it to `dispenser_Rb__A`, which is what the paper already used.

Still open in this group, and genuinely drift rather than defect: `sane_state` / `default_state`; stage names `MOT_Delta`, `OP`, `MT` against the demo's and the paper's longer forms; composition written imperatively in `prepare_sample` rather than with `cascade` (which the lab's parameter names would not currently survive — its own `KNOWN_ISSUES.md` L6). The lab also has a `dispenser_Rb__A` connection and device that `sec:demonstration` shows but the shipped demo does not.

*ADbasic.* **RESOLVED 2026-09-15** (issue #86). The dispatch subroutine was `processSwitches` in `resources/ADwin/WignerTimeADwin.bas` against the paper's `processUpdates`; it is now `processUpdates` in both `.bas` files, along with the `dim` comments that described the same arrays as "switches". Verified that the subroutine is now line-for-line identical to the `sec:adwin` listing, ignoring blank and comment lines. **Not compiled or run** — see §E.

**Prerequisites 1 and 2 are DONE as of 2026-09-03** (commits `76b5d09`, `629baef`): the manuscript was imported from Overleaf and committed as a self-contained subtree, `docs/paper/` — `main.tex`, `SciPost.cls`, `SciPost_bibstyle.bst`, `WignerTime.bib` and all five figures. Every `\includegraphics` target and the bibliography call resolve, so the canonical target is now under version control and buildable. Verified separately that that import was byte-identical to the copy audited on 2026-09-01/02 (1453 lines, every recorded citation on the same line).

**Re-imported 2026-09-15** as the arXiv version (`fdd2e0d`), now 1458 lines: licence corrected to GPLv3, three affiliations added, `orcidlink` loaded, an acknowledgement of the review paragraph added, and the `sec:forwarding` listing set in `\scriptsize`. None of it touches the listings this inventory is about, but **line numbers quoted anywhere in this document have shifted by up to +5 below `sec:goals`** — the device tables are now at `main.tex:434` and `:1022`, and the `connections` prose at `:998`.

**One prerequisite remains, now half-satisfied.**

1. **Land the pending decisions first.** The §C decision has two halves. *Event functions lose `**kwargs`* **landed 2026-09-16** (`19d41ad`), and the demo, the lab and the manuscript were rewritten together, so `sec:demonstration`, `sec:stacking`, `sec:interweaving` and `sec:forwarding` are already reconciled on that point. *`finish` derives the final state from the timeline* has not landed, and still rewrites `finish` in both the demo and `sec:demonstration`. The parameter-style divergence listed above is unaffected by either and remains the bulk of this item.

### D8 — `"variable"` resolves only on one call path **[new, found 2026-09-03]**

The literal string `"variable"` is not handled by `_to_col_var` at all. It is substituted for the actual variable name inside `origin.update`'s `find_every_origin` loop, before `find` is reached. So it works through `update`, `ramp` and `anchor`, and raises `variable is an unsupported option for 'origin'` when `origin.find` is called directly with it — even though `find` is the function whose docstring enumerates the reserved labels, and `_ORIGINS` lists `"variable"` among them.

Not user-visible today, but it means `find` cannot be tested or reused in isolation for the one origin keyword that matters most to `ramp`.

### D9 — the decision-tree figure and the config disagree on the value slot **[new, found 2026-09-03]**

`graphic/origin-decision-tree-highlighted.png` (`fig:origin`) shows the default as `[["anchor", 0.0], ["last", 0.0]]`. `config.ORIGIN__DEFAULTS` is `[["anchor", None], ["last", None]]`. Numerically they agree, since a value origin of 0.0 and an absent value origin both leave values untouched, but they are different objects and only one is what the code does. Whichever way it is settled, the figure and the constant should say the same thing — and if the default stops living in `config`, as proposed, the figure's root node needs rewording rather than renumbering.

### D10 — `ensure_pair` message typo, and `find` normalises twice **[new, found 2026-09-03]**

`internal/util.ensure_pair` raises a message beginning "Two many arguments to" — "Two" for "Too". Reachable from user input: `origin=["a", "b", "c"]`.

Separately, `find` normalises the origin twice: once at the top, for the `[None, None]` early return, then again through `sanitize_origin`. Harmless, but it means `sanitize_origin`'s "timeline required for a string origin" check does not gate the early return, and a reader cannot tell which normalisation is authoritative.

### D11 — `conversion.add` is hard-wired to ±10 V / 16 bits, ignoring the per-module specification **[new, found 2026-09-12]**

`adwin/internal.py::add` takes `machine_specifications` and uses it for `modules__digital` and `add_cycle`, but calls `conv.add(dff)` with no specifications at all. The analog conversion therefore always uses `conversion.SPECIFICATIONS__DEFAULT` (`voltage_range=[-10.0, 10.0]`, `num_bits=16`, `gain=1`) and never consults `machine_specifications["modules"]`, which carries a `voltage_range` and `bits` per module precisely so that modules can differ.

Harmless on the setups tested, where every analog module is ±10 V/16-bit — which is why the demo and the lab's timelines convert correctly. But a module with any other range is silently mis-converted, with no error and no warning, and the function's own signature says otherwise. Same shape as A-class silence rather than a crash.

Found while verifying the conversion arithmetic end to end for the lab's device table.

### D12 — digital modules are identified by `bits == True` **[new, found 2026-09-12]**

`adwin/internal.py::modules__digital` selects modules with `m.get("bits", False) == True`. The digital module is declared with `bits: 1`, and is matched only because `1 == True` in Python.

It works, and module 1 does come out as the digital one. But the test expresses "has exactly one bit" as a comparison against a boolean, so a module declared `bits: 2` would not be caught, and the intent is not recoverable from the code. `m.get("bits") == 1` would say it.

### D13 — `cycle_period__normal__us` is named in microseconds and holds seconds — **RESOLVED AND FIXED 2026-09-15**

`adwin/internal.py` set `"cycle_period__normal__us": 5e-6`. The `__us` qualifier said microseconds; the value was 5 µs expressed in seconds. The arithmetic was right and only the name was wrong — but wrong in the one place a reader checking a factor-of-10⁶ question would look.

`normal` turned out to be a fossil rather than a choice. The original specification (`099e65c`) read

```python
"cycle_period__normal": 5e-6,
"cycle_period__burst":  250e-9,
```

where `burst` was ADwin's ADC burst sampling mode (`P2_Burst_Init` in `WignerTimeADwinADC.bas`). When the per-device nesting was flattened, `burst` was dropped and `__us` appended, leaving `normal` qualifying a contrast that no longer existed.

**Fixed.** The key is now `cycle_period`, in seconds like every other time in the package — no unit suffix, because nothing else carries one (`TIME_RESOLUTION`, `time`, `duration`, `time_resolution` are all bare seconds) and a suffix is what rotted in the first place. The name is consistent with the `cycle` column and the `add_cycle` function that produce it. A comment at the definition records the burst history and states that if ADC burst mode is ever described here it wants a name of its own (`sampling_period__ADC`): it is a sampling period, for reading, on a different clock — filing the two as flavours of one "cycle period" is what made the qualifier necessary.

Two adjacent defects in the same three lines were fixed with it:

- the `KeyError` handler raised a message naming `cycle_period__normal`, already out of sync with the key it had just failed to find, sending the reader after the wrong string;
- that message interpolated `{device}`, which is not a parameter of `add_cycle` but the imported `wignertime.device` **module**, so it rendered as "… not found in specifications for `<module 'wignertime.device' from 'C:\…\device.py'>`". A leftover from when the function took a `device` argument selecting among `device_001`/`device_002`. pyflakes could not catch it precisely because the name happens to be bound at module scope. It now lists the keys that *are* present.

The `add_cycle` docstring also documented two parameters (`specifications`, `device`) that the function does not take.

This is a breaking change to `SPECIFICATIONS__DEFAULT` for anyone passing their own `machine_specifications`, but it breaks loudly and the new message names the missing key. Nothing in this repo or in `quantum_optics_lab` passes one — which is D15's complaint from the other direction. Suite 209 passing; demo and lab timelines convert to identical output (8260/35 and 8188/33).

Tracked as [#127](https://github.com/WignerQuantumOptics/Wigner_Time/issues/127), and as L18 in `quantum_optics_lab`.

### D14 — nothing cross-checks ADbasic's `Initial_Processdelay` against the cycle period **[new, found 2026-09-12]**

`resources/ADwin/WignerTimeADwin.bas` carries `Initial_Processdelay = 5000` in its header; `adwin/internal.py` carries `cycle_period = 5e-6` seconds (renamed from `cycle_period__normal__us` by D13). These must agree, and nothing checks that they do: they live in different files, in different languages, in different units, and the Python side never reads the `.bas`.

They agree today, so this is latent. But it is exactly the pair that drifts when someone raises the Processdelay on the machine to buy resolution and does not think to change Python — and the resulting error is a *uniform rescaling of every time in the experiment*, which is a more plausible thing to misread as a physics result than as a bug. Reading the value back off the machine, or at minimum asserting it in `adwin.core.create`, would close it.

Worth noting what makes this more than pedantry: the same reasoning is why the maintainer could dismiss a suspected 5× cycle-period discrepancy immediately — a timeline that took five times as long as expected would be noticed at once. That argument protects against a *change* in the ratio, not against the two values having been inconsistent from the start, and only while someone is watching the clock.

### D15 — `adwin.core.create` silently ignores two of its own arguments **[new, found 2026-09-11]**

```python
def create(timeline, connections, devices, machine=None,
           machine_specifications=ad.SPECIFICATIONS__DEFAULT, time_resolution=None):
    ...
    output = convert(timeline, connections, devices)   # neither is forwarded
```

`convert` accepts both parameters and `create` accepts both parameters, but `create` passes neither on. So `create(..., time_resolution=1e-6)` expands the ramps at the default cycle period, and `create(..., machine_specifications=...)` converts against the default machine — in both cases with no error and no warning.

Worse than merely ignoring them: `machine_specifications` *is* still used, for the `time_end` that `create` prints. The number reported to the user is computed from the specification they supplied; the data uploaded to the machine is not. The one visible signal therefore agrees with the user's intent while the hardware disagrees with it.

`create` also prints that line unconditionally, where the `initialize_ADwin` it replaced took `printDiagnostics=False`. In a parameter scan that is one line of noise per point, interleaved with the caller's own output. Reported from live use in `quantum_optics_lab`.

### D16 — the anchor label cannot be printed on a legacy Windows code page **[new, found 2026-09-11]**

`config.LABEL__ANCHOR` is `⚓` (U+2693). Printing a timeline containing an anchor from a console whose encoding is a legacy Windows code page — cp1250 on the Hungarian-locale machines this package is developed and used on — raises:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2693' in position 706
```

This is not obscure: the recommended convention is that *every user-defined stage ends with an anchor*, so essentially every real timeline contains one, and `print(timeline)` is the most obvious thing a user does with it. Jupyter and any UTF-8 console are unaffected, which is why it has gone unnoticed — but it means the package's own advice produces objects that cannot be inspected from a plain terminal without setting `PYTHONIOENCODING`.

Loud rather than silent, so low severity by this document's ordering. Fixing it properly probably means making the label configurable rather than changing it, since it is also a display affordance.

### D17 — a `stack` constituent that was never called binds the timeline to its first parameter — **FIXED 2026-09-16**

`stack(timeline, demo.MOT)` -- the stage's name where its call belongs -- composed silently, binding the 18-row timeline to `MOT`'s `duration` and returning a function where a timeline was expected. It was caught only when something followed it in the chain, so the hole was at the tail of every composition.

**Fixed by tagging.** `internal/util.function__lambda` and `timeline.stack` now mark what they produce with `ATTRIBUTE__DEFERRED`, and `stack` checks each constituent. The tag is necessary because the distinction is invisible otherwise: a deferred call, a composed `stack` and an uncalled stage are all plain `function` objects, and their signatures do not separate them.

A hand-written `lambda tline: expand(tline, ...)` is a legitimate constituent and carries no tag, so an untagged callable is accepted when it takes **exactly one required positional argument** (`util.takes_one_timeline`). That discriminates precisely the case at issue: a stage written to the manuscript's convention defaults everything and takes `timeline=None`, so it has *none*; a stage with required parameters, like `pull_coils`, has several. Only a transformer has one. `timeline.as_deferred` is exposed for anything the heuristic would turn away, and the error message names it.

Two consequences beyond the bug:

- **`noop` is no longer `funcy.identity`.** It has to carry the tag, and tagging a shared library function would mark it for every other user of `funcy`. It is now `lambda timeline, **kwargs: timeline`, which also means it survives a `stack` that forwards keywords — `identity` raised `TypeError: identity() got an unexpected keyword argument 'context'`, recorded as L5 in `quantum_optics_lab`.
- A frame passed as a *constituent* rather than as the leading argument is now rejected with a message, instead of `'DataFrame' object is not callable` from inside the composition.


---

## E. Testing constraints

**A green test suite does not clear the ADwin backend.** `ADwin` is an optional extra (`[tool.poetry.extras] adwin`) and the hardware is not present in a development environment. Changes under `wignertime/adwin/` can only be checked for internal consistency; correctness must be verified on the rig. Flag any such change explicitly rather than reporting it as done.

Note that the extra being installed is *not* the same as the hardware being present: `ADwin` is a pure-Python wrapper and installs fine on a development machine, so `adwin.core` imports and its pure functions (`convert`, and everything under `adwin.internal` and `adwin.validate`) are genuinely exercised by the suite. What remains unverifiable locally is anything that talks to a device — `link_device`, and the `Set_Par`/`SetData_Long` calls in `core.create`.

~~The same applies to `conversion.function_from_file`, which reads calibration data (e.g. `resources/calibration/aom_calibration.dat`) that will not exist in a clean checkout.~~ **Withdrawn 2026-09-01: this is wrong.** `resources/calibration/aom_calibration.dat` is tracked by git and present in a clean checkout, and the demo's `AOM_science__trans` device reads it during ordinary test collection.

**"If the suite errors rather than skipping cleanly when an optional extra is absent, fix that first" — done, 2026-09-01.** See F.


---

## F. Resolved — do not re-report

- **`drop_repeats`** in `adwin/validate.py` — designed and committed.
- **`drop_duplicates`** already uses `keep="last"`, not `keep="first"`.
- **`conversion.to_digits`** already rounds correctly; the TODO suggesting otherwise is stale.
- **D1, the `origin.py` self-import** — diagnosed (a module importing itself, no duplication) and removed, 2026-09-01. See D1.
- **`drop_repeats` emitted a pandas downcasting `FutureWarning` on every real ADwin export** — fixed 2026-09-01. Reported from live use of `adwin.convert`.

  `mask__changed` is computed over the non-special rows only, then widened back to the full index. `reindex` without a `fill_value` fills the added labels with NaN, which `bool` cannot hold, so the mask silently upcast to `object` dtype — and `fillna` on an object-dtype array is the deprecated operation. Fixed by `reindex(timeline.index, fill_value=False)`, which never introduces NaN and so needs no `fillna` at all. The same latent pattern in `internal/dataframe.mask__changed` was changed with it; it never warned, because there the reindex is onto a permutation of the same index and adds no labels.

  Worth noting *when* it fired, because it explains why the test suite under-reported it: only when special-context rows are present, which is the only case where the run rows are a strict subset. That is every real export and only 5 of the tests.

  Outputs verified byte-identical to a pre-fix snapshot across three shapes (special contexts present, absent, and two channels) with `assert_frame_equal`, and `adwin.convert` on the full demo now runs clean under `-W error::FutureWarning`. Regression tests added to `test_drop_repeats.py`: one promoting `FutureWarning` to an error, one pinning the mask's dtype.

  **One pandas `FutureWarning` remains in the suite**, unrelated and untouched: `assert_frame_equal` in `internal/dataframe.assert_equal` reports "Mismatched null-like values None and nan" from the `test_file.py` round-trip tests, and will raise rather than warn in a future pandas. It encodes a real question — whether a `None` that comes back from JSON/parquet as `NaN` should compare equal — so it is a semantic decision, not a mechanical fix. Not filed above because it is a test-comparison issue rather than a library defect, but it will need answering before a pandas 3 upgrade.

- **Nesting one deferred core call inside another now raises at the point of the mistake** — fixed 2026-09-01.

  `create`, `update`, `ramp`, `anchor` and `expand` return a callable when called without a `timeline`, and that callable is not a timeline. Nesting them — `expand(ramp(...), time_resolution=1e-4)`, which reads like ordinary composition — passed a function in as the `timeline` argument, where it survived the `timeline is None` test and failed later on the first dataframe attribute touched: `AttributeError: 'function' object has no attribute 'columns'`, naming neither the function at fault nor the real error. Reported from live use.

  Fix: `internal/util.ensure_not_deferred`, called as the first statement of all five. It raises `TypeError` naming the function, explaining that a core call without `timeline=` returns a function, and showing the sibling-in-`stack` form that was intended. Regression tests in `test/wigner/time/timeline/test_timeline_deferred.py` (11 cases, covering all five functions, the deferral protocol itself, and that `stack`/`cascade` still accept a leading callable — they legitimately do, and must not be caught).

  This is a guard, not defensive branching: it converts a downstream `AttributeError` into an immediate, named `TypeError`, which is what §"loud and early" asks for. It is deliberately narrow — it fires only for a callable given where a timeline belongs, the mistake the deferral design specifically invites, and is not a general type check on the argument. A non-callable non-frame (`expand([1, 2, 3])`) still fails downstream and cryptically; broadening it would mean deciding what counts as a timeline, which is entangled with the `wt_frame.CLASS` polars abstraction (D5).

  **That rationale is withdrawn, 2026-09-03.** It does not hold: the check would route through `wt_frame.CLASS`, which is precisely the seam that exists for the polars swap, so there was no cost to broadening it. The narrowness was agreed insufficient in discussion and the full contract is recorded as C4. Until C4 lands, the cryptic failures it lists remain reachable.

  Worth noting what the guard does *not* address, since the original report was really about something else: `expand` acts on the entire timeline it receives, not on the ramp beside it. Calling it mid-`stack` inside a late stage expands **every** ramp accumulated so far — 14 variable-ramps across five variables by the time `finish` runs in the demo — at whatever `time_resolution` was passed, and then drops the `function` column so that the `expand` inside `adwin.core.convert` silently becomes a no-op and that resolution is what reaches the hardware. Per-ramp resolution is available instead by baking it into the `function` argument, as `demo.pull_coils` already does. Both behaviours are by design; neither is documented anywhere a user would look, which is a documentation gap rather than a bug.
- **E, the suite aborting when an optional extra is absent** — fixed 2026-09-01.

  Measured before: hiding `ADwin` produced 6 collection errors and hiding `matplotlib` 3, and because these were *collection* errors pytest aborted the run in both cases, so **zero** tests executed. The suite could not be green for the right reasons; it could only be green or absent.

  Root cause was not the guarded modules themselves but three dead module-scope imports of them, each supporting only commented-out code: `demo/full_experiment.py` imported `adwin.core` for a commented hardware call, and `test_demo.py` and `test_timeline_ramp.py` imported `adwin.display` for commented debug plots. Because `test_file.py`, `test_timeline_ramp.py` and `test_timeline_manipulate.py` all import the demo, one unused import in it took out five unrelated modules.

  Fix: deleted the three dead imports, leaving a comment at each commented-out call site recording what to import and which extra it needs; added `pytest.importorskip` to the one module that genuinely needs `ADwin` (`test_adwin.py`) and the one that genuinely needs `matplotlib` (`test_display.py`).

  Measured after — full install 193 passed; `ADwin` hidden 187 passed / 1 skipped; `matplotlib` hidden 192 passed / 1 skipped. No collection errors in any configuration.

  Two notes for whoever revisits this. First, guarding is the wrong instrument for a dead import — an early attempt used `importorskip` on all three modules and needlessly skipped ~120 tests that never touch matplotlib; check whether the import is *used* before guarding it. Second, `pip install wigner-time` without the `adwin` extra could not import `wignertime.demo.full_experiment` at all, so this was a packaging bug as well as a test-hygiene one; worth confirming as part of the pre-publication checks alongside C1.

---

## G. Standing rule: writing friction is a design signal

The paper and the code are developed together. If a behaviour is awkward to describe in prose, the default response is to change the code, not to write defensive prose around it.

Corollary for code work: if a change makes an existing claim in the manuscript inaccurate or hard to state, **stop and report it** rather than proceeding. Do not edit the paper to match the code.