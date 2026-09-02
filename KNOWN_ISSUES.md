# Wigner Time — known issues

Standing checklist for code work. Written for an agent picking up the repository cold.

**Provenance.** Originally derived from snapshots of `timeline.py` and `origin.py` plus design discussion. **Verified against the live repository on 2026-09-01, branch `drop_repeats` (34104ce).** Every item below was checked against the code as it stands; the ones that were reproduced empirically say so and give the repro. Line references are deliberately omitted; anchor on function names. Both **[verify]** items (A4, D1) are now resolved — see their entries.

**Priority order.** Silent failures rank above visible ones. A wrong answer that raises is a nuisance; a wrong answer that returns quietly can sit in an experiment for months.

Item IDs are stable — they are cross-referenced from `CLAUDE.md` and from C1 — so verification has *not* renumbered them, and sections A and B are consequently no longer in strict severity order. **A4 is now the most severe open item in this document**: it was expected to be unreachable and turns out to be reachable through `ramp`, silently, on any anchorless timeline. Read A4 first.

**Do not "fix" by adding try/except or defensive branching.** This library's value proposition is that experiment descriptions are inspectable data. Failures should be loud and early, at the point where the user's intent was ambiguous — not absorbed downstream.

---

## A. Silent failures

### A1 — `cascade` discards unmatched keywords

`timeline.cascade`. The dispatch loop iterates over `kws`, tries each function name, and `break`s on the first match. If no function name matches, nothing is appended to `result` and the keyword vanishes. No warning, no exception.

Consequence: a typo in a stage prefix (`molases_duration=...`) means the parameter is silently ignored and the stage runs with its default. In an experimental timeline that is a physically wrong sequence which still executes.

Fix direction: collect unmatched keys and raise, listing them alongside the available function names. This is layer 1 of the three in §C “Design intent”, so it does not conflict with keyword forwarding.

### A2 — `cascade` uses substring matching, not prefix-anchored matching

The test is `if fname in k`, and the split is `k.split(fname, 1)[1]`. Correctness currently rests entirely on `sorted(f_names, key=len, reverse=True)`: `MOT_detuned_growth_duration` resolves correctly only because the longer name is tested first.

Two distinct hazards, worth keeping separate:

- **Stage named after another stage** (`MOT` / `MOT_detuned_growth`) — the genuine collision. If `MOT` itself had a parameter called `detuned_growth_duration`, the keyword `MOT_detuned_growth_duration` would be captured by the longer stage name and `MOT`'s parameter would be permanently unreachable.
- **Parameter merely containing a stage name** — harmless under prefix anchoring, hazardous under substring matching. Anchoring the match to the start of the key removes this class entirely.

Fix direction: anchor with `k.startswith(fname + "_")`, and resolve genuinely ambiguous splits by consulting the target functions' signatures (`inspect.signature`) — accept the split only if the remainder is a parameter the function actually takes. See C1 for the associated API decision.

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

### C1 — Should `cascade`'s signature checking default to strict?

Two candidate behaviours: strict (consult `inspect.signature`, reject splits that don't correspond to a real parameter) or lenient (longest-match-wins, as now). Strictness is consistent with the paper's claim that parameter sets are explicit and checkable, and it subsumes A1 and A2. Cost is that it breaks `**kwargs`-forwarding stages, of which the lab example has several. Decide before PyPI publication; changing a default afterwards is expensive.

### C2 — Should `create` accept origin parameters?

`create` passes `origin` straight to `wt_origin.update`, while `update` first routes through `wt_origin.auto`. This asymmetry may be deliberate (`create` starts a timeline, so has nothing to be relative to) or vestigial. Unresolved.

### C3 — `anchor` with `t=None`

The docstring carries an unresolved TODO asking what happens if `t` is unspecified, with the author's own guess that it fails. Establish the intended behaviour and either give `t` a meaningful default or reject `None` explicitly.

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

`docs/main.tex` is canonical. Where the code and the manuscript disagree, **the code changes.** This is the same direction as §G: the manuscript is not to be edited to match the code.

**Scope to settle before starting.** The paper fixes the naming of everything it *shows*; for library internals it never shows there is no paper version to reconcile to, so those are out of scope by construction. Proposed reading: reconcile the public API surface, the demo, and the ADbasic listing; leave internal identifiers (`num__bounds`, `column__value`, `timeline__past`, `mask__changed`) alone. Confirm this before renaming anything, because the alternative reading — that the paper's single-underscore style governs internals too — is a very large change.

Do not conflate the two naming systems:

- **Variable names** — `<device>_<UID>(__<unit>)`, enforced by `variable.REGEX` and by `connection.new`. Paper and package already agree here; this system is load-bearing and settled.
- **Python identifiers** — stage parameters and keyword names. The package uses `__` as a qualifier separator, the paper's listings use a single `_`. This is where the divergence lives.

Known divergences, as an inventory rather than a plan:

*Shipped demo (`src/wignertime/demo/full_experiment.py`) against `sec:demonstration`.* Parameter style throughout (`duration__coil_ramp` / `duration_coil_ramp`, `lag__MOTshutter` / `lag_MOT_shutter`, `li`,`ui` / `lower_current_initial`,`upper_current_initial`, `toMHz` / `to__MHz`); `shutter_OP001`,`shutter_OP002` / `shutter_OP1`,`shutter_OP2`; `MOT__detuned_growth` / `MOT_detuned_growth`; `pull_coils(duration, l, u, lp, up, pt)` / `pull_coils(duration, lower_current, upper_current, pt)`; the paper has a `MOT_off` stage and a `delay_shutter_reinitialization` parameter that the code inlines as `0.1`; the paper's `magnetic_trapping` gives `context` to `anchor` rather than to `stack`; `wtf.save` / `wtfile.save`.

*Real lab code (`experiment.py`, `diagnostics.py`) against the current package.* Targets the pre-restructure `wigner_time`: `con.connection(...)` for `adcon.new(...)`, and `devices` as a raw frame with `unit_range`/`safety_range` for `device.new(...)` with `to_V`/`value__min`/`value__max` — the schema `internal/timeline/validate.py` still expects (see the note on that module in `CLAUDE.md`). `sane_state` for `default_state`. Stage names `MOT_Delta`, `OP`, `MT` against the demo's and the paper's longer forms. Composition written imperatively in `prepare_sample` rather than with `cascade`. Several variable names violate `variable.REGEX` and would now be rejected outright by `connection.new`: `dispenser__A`, `AOM_OP_aux`, and every three-part coil name. **This group contains a live bug, not just drift** — the stage functions write `coil_MOT_lower__A`, `coil_MOT_upper__A`, `coil_MOT_lower_plus__A`, `coil_MOT_upper_plus__A` and `shutter_transverse_pump` while the connection table declares `coil_MOTlower__A`, `coil_MOTupper__A`, `coil_MOTlowerPlus__A`, `coil_MOTupperPlus__A` and `shutter_transversePump`. Different strings, so the join in `adwin.internal.add` misses and `remove_unconnected_variables` drops all five silently: the coils would never actuate. Verify against the running rig before assuming it is only a transcription slip.

*ADbasic.* The paper calls the dispatch subroutine `processUpdates`; `resources/ADwin/WignerTimeADwin.bas` calls it `processSwitches`.

**Three prerequisites, all cheap, all worth doing first.**

1. **Commit `docs/main.tex`.** It is currently untracked. A canonical target that is not under version control cannot be reconciled against — there is no way to tell whether the code drifted or the manuscript moved.
2. **Make the manuscript build.** There is no `docs/graphic/` and no `WignerTime.bib`, and two referenced figures exist nowhere in the repository (`origin-decision-tree-highlighted.png`; `ramp-options` only as `.svg`). See `CLAUDE.md` for the full asset list.
3. **Land the pending decisions first.** The §C decision (event functions lose `**kwargs`; `finish` derives the final state from the timeline) rewrites much of the demo, and hence much of `sec:demonstration` and the new `sec:forwarding`. Reconciling before that lands means doing the same renaming twice.

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

  This is a guard, not defensive branching: it converts a downstream `AttributeError` into an immediate, named `TypeError`, which is what §"loud and early" asks for. It is deliberately narrow — it fires only for a callable given where a timeline belongs, the mistake the deferral design specifically invites, and is not a general type check on the argument. A non-callable non-frame (`expand([1, 2, 3])`) still fails downstream and cryptically; broadening it would mean deciding what counts as a timeline, which is entangled with the `wt_frame.CLASS` polars abstraction (D5) and was left alone.

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