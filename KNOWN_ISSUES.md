# Wigner Time — known issues

Standing checklist for code work. Written for an agent picking up the repository cold.

**Provenance.** Originally derived from snapshots of `timeline.py` and `origin.py` plus design discussion. **Verified against the live repository on 2026-09-01, branch `drop_repeats` (34104ce).** Every item below was checked against the code as it stands; the ones that were reproduced empirically say so and give the repro. Line references are deliberately omitted; anchor on function names. Both **[verify]** items (A4, D1) are now resolved — see their entries.

**Priority order.** Silent failures rank above visible ones. A wrong answer that raises is a nuisance; a wrong answer that returns quietly can sit in an experiment for months.

Item IDs are stable — they are cross-referenced from `CLAUDE.md` and from C1 — so verification has *not* renumbered them, and sections A and B are consequently no longer in strict severity order. **Section A is closed** (A15, found 2026-09-23, was fixed the next day). **Section B is closed apart from B10**, which raises rather than misleading, and **B11**, which is new on 2026-09-22 and is the only item here whose failure mode is physical rather than numerical. The rest of the open work is in sections C and D, and the D items cluster: D11, D14, D15, D18, D19, D20, D21 are all the ADwin backend, and are being done in one pass. The roadmap is at #94, and the work is on the branch `issue#94`, where D15 and D20 are fixed and D19 is guarded on the Python side (2026-09-23). Resolved entries are kept, with an account of what replaced each, because the measurements are the argument for the design that replaced it.

**Origins have their own reference.** `docs/origin-resolution.md` maps every branch of the origin mechanism as implemented, in four layers, with the defect in each. Read it before touching `internal/origin.py` — the items below give the defects, that document gives the shape.

**Do not "fix" by adding try/except or defensive branching.** This library's value proposition is that experiment descriptions are inspectable data. Failures should be loud and early, at the point where the user's intent was ambiguous — not absorbed downstream.

## How work is tracked

Every item here has a GitHub issue, and the two carry different things. **This file holds the diagnosis, the measurement and the reasoning; the issue holds the state.** Annotate both — an issue with neither milestone nor label is invisible to every view that matters.

**An issue is closed when it is resolved on the main development branch**, not when that branch reaches `main`. The branch is currently `issue#94`, which will eventually be merged into `claude_code` (maintainer, 2026-09-23). Closing as work lands is also what makes a parent issue's sub-issue count show progress. The roadmap at #94 is tracked that way.

**Milestones say _when_.** Their descriptions on GitHub are authoritative; reproduced here because they are otherwise recorded nowhere in the repository.

| milestone | what belongs in it |
| --- | --- |
| `10 — paper` | Must land before the SciPost paper is published: silent-failure defects, anything that falsifies `docs/paper/main.tex`, and the decisions those depend on. |
| `20 — internal API` | The #9 subtree — dataframe backend abstraction, public/internal API separation, util reorganisation. Deliberately deferred past the paper. |
| `30 — reach & polish` | Hardware breadth, display and ergonomics, performance, outreach. Nothing here blocks publication. |

**Types say _what the work is_.** Org-level GitHub issue *types*, not labels, and a separate axis from both of the others — which is why a search for a "decision label" finds nothing and the wrong conclusion was drawn here until 2026-09-22.

| type | what it means |
| --- | --- |
| `Bug` | An unexpected problem or behavior |
| `Task` | A specific piece of work |
| `Feature` | A request, idea, or new functionality |
| `Decision` | An open API or design decision that must be settled before dependent work can proceed |

`Decision` is the tracker's counterpart of §C, and carries "flag and ask, never settle unilaterally" onto GitHub. Set it on anything whose entry here offers two options rather than a fix. Open `Decision` issues as of 2026-09-23: **#85, #97, #133, #143, #144, #145** (#53 was settled and closed on 2026-09-23). #85's direction was settled on 2026-09-25 (C7); it stays a `Decision` until its name and its two open details are.

**Labels say _what kind_.** `silent` (a wrong answer with no error — outranks visible failures, and puts the item in `10 — paper` by default); `paper-affecting` (falsifies a claim in `main.tex`, so §G applies and the *code* changes); `consistency` (causes mental friction); `potentially surprising` (not wrong as such, but likely to surprise a user); and the area tags `ux`, `performance`, `docs`, `adwin`, `origin`.

**The section letters here are not the labels.** A is silent failures, B correctness, C open decisions, D structural — but a D item can be `silent` (D11, D14, D15, D18 all are), so set the label from the behaviour rather than from the letter.

**One gap, not two — the first was an error of mine, corrected 2026-09-22.** This paragraph claimed there was nothing on the tracker for an open decision. There is: the `Decision` issue **type** above, in use since before the claim was written (#83, #95–#98). It was missed because the search was for a *label*, and types are a third axis. Every open issue now carries a type; the ten that did not were all filed from here, the same oversight as the milestones before them. The real remaining gap is compatibility work (#88, Pandas 3), which has no label and no obvious type.

**What `paper-affecting` currently covers, as of 2026-09-22.** Four issues carry the label — #136 (B10), #121 (D7), #85, and #143 (`t` vs `time`, filed the same day) — and on review that undercounts. **#133 (D18) belongs in the set**: `sec:adwin` states that "ADwin is modular, so which channel types are available is a question of which modules are installed, not of the control software", and a backend that writes every digital update to module 1 makes that false for a second digital module. Two further paper items are tracked by no issue at all:

- ~~the manuscript in `docs/paper/` has **local changes since the arXiv import** that have not been carried back to Overleaf.~~ **Done 2026-09-23**: carried across by the maintainer, and the committed file is canonical again. The inventory, `docs/paper/CHANGES-since-arXiv.md`, was deleted with it;
- ~~**`sec:stacking` calls `trigger_camera(0.0,1e-3)`** without the `context` its definition requires.~~ **Fixed 2026-09-23**, with two more errors found by running the listing: `init` called `anchor()` although `t` is required, and never set the coils that `MOT` then ramps, so the ramp raised for lack of a start. The call now names `"imaging"`, `init` sets both coils to zero and anchors at `0.0`, and the listing runs as printed. The listing was unchanged since the Overleaf import; the coil error became an error on 2026-09-18, when a ramp from nothing stopped starting at zero silently. The rule itself is stated in `sec:functions` (“What a ramp refuses”);
- **The opening listing of `sec:definitions` (main.tex:452–487) does not run** (found 2026-09-25). `shutter_MOT= 0` lacks its comma; `detuned_growth` ramps `lockbox_MOT__MHz`, which is never set, so the ramp raises (“What a ramp refuses”); and `final`, a table, fails as a later constituent of `stack` with `'DataFrame' object is not callable` (see D17's correction). **Folded into #85 (C7)** rather than fixed here: its `final = initial.copy()` cannot survive that change anyway, since `initial` becomes a stage. The listing is otherwise already written as C7 would have it — `stack(initial, MOT, detuned_growth, final)`, four peers — and what `final` means, one state in two contexts, is a function of the context: `default_state` in miniature, which `sec:discussion` argues for;
- **In the same `init`, the `create` rows got no context.** `create` has already produced a timeline when `stack` receives it, so `stack`'s `context="initialization"` reached only the anchor. **Listing fixed 2026-09-23**: the context is now given to `create`, and the anchor inherits it. **The behavior of `stack` is unchanged and still open**, as C6 (#145): with a reserved context it silently changes the hardware sequence;
- ~~**The initial/final-state listing in `sec:functions` did not run.**~~ **Fixed 2026-09-23.** It read `final = init` (undefined; `initial` was meant), and even as `final = initial` the next line would have relabelled `initial` too, since both names hold one table: in-place modification, which the paper argues against. Now `final = initial.copy()`. Its `import timeline as tl` is also corrected to `from wignertime import timeline as tl`, as in the paper's other listings;
- ~~**`sec:interweaving` pointed to `sec:demonstration` for further examples**, and that listing has none.~~ **Fixed 2026-09-23**: the section now shows `trigger_camera` placed at `origin="molasses"` into the complete `timeline__demo`, the case `test_demo.py` checks (#53), and points to `sec:parameter_scan` only. Its claims were checked against the real `timeline__demo`: the exposure runs 2.0–3.0 ms after molasses, inside magnetic trapping (0.58–3.63 ms), and no existing row moves;
- **#142 is very likely a fifth**, though it is not labelled: it proposes replacing `origin=None` with a visible default, and `sec:functions` shows `origin=None` in the signatures of `update`, `ramp` and `anchor`. Flagged on the issue rather than labelled unilaterally, since it is the maintainer's own;
- ~~`sec:discussion` carries a **commented-out paragraph** describing bit-flip-timed ramps, per Kowalski *et al.*, as future work.~~ **Done 2026-09-23.** Revived in the present tense and moved to `sec:adwin`, after the event-loop paragraph. That is where the conversion is described, and it leaves the Discussion's list of *remaining* gaps, where a done item does not belong. The paragraph states what the package uploads. `drop_repeats` itself has **not yet run on the rig** (the Lab2 fixture's archived tuples predate it), so the claim rests on the code, not on an observation of the hardware. Distinct from #87, which is about doing the expansion that way in `expand`.
- **`sec:parameter_scan` calls `adwin.create` pure** (main.tex:1446): "it constructs a backend object without side effects". It has them: it writes `Par_1..3` and the data arrays on the machine, and with no `machine` it opens a connection to device 1. The listing works regardless, because each upload finishes before the start that follows it. Found 2026-09-23. **Settled the same day by the maintainer's decision on roadmap step 5 (#94), and the manuscript changed with the code, at his request.** `create` is renamed `upload`: the old name suggested building something and could be confused with `timeline.create`, while the paper had always called this step an upload (main.tex:518, 850, 882). It requires the machine and the process, and returns a record of the upload whose first two fields are the machine and the process. main.tex:818 now describes `upload`. `sec:demonstration` obtains the machine with `link_device`, uploads to process 1 and starts it. At :1446 the scan passes the record, which names the machine and the process, straight to the camera routine; the next paragraph's "impure hardware execution" now agrees with it. Both listings were run against a stand-in machine and work as printed.

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

### A3 — `ramp` computes cleaned frames and then discards them — **RESOLVED AND FIXED 2026-09-18**

**Maintainer decision: split the two degeneracies.** The mask conflated things that are not alike.

- A zero **duration** has no sensible expansion, since both boundaries occupy one instant, and is almost always a slip in the caller's arithmetic — a `duration` that came out of a subtraction as 0. It now **raises**, naming the variables and the instant.
- A **negative** duration is the same error with a sign, and was the worse of the two: `expand` sorts each ramp's boundaries by time, so the endpoints were silently exchanged. See A12.
- A zero **value change** is a *hold*. It occupies time, so discarding it shortened the timeline and pulled everything after it forward. It is now **kept and expanded**. The identical rows that produces are removed again by `adwin.validate.drop_repeats` before the hardware, which keeps the first and last row of each channel — so the redundancy is paid for in the device-layer table only, and that table is the thing the user is meant to be able to read.

The verified symptom is gone. `cascade(demo.init, demo.MOT, demo.finish)` now carries its final ramps:

```
before: finalRamps variables = ['⚓_002']
after:  finalRamps variables = [6 coils, lockbox_MOT__MHz, '⚓_002']
```

The full demo and the lab timeline hash identically before and after, neither containing a degenerate ramp. `test_rampDoesNotRaise2` and `...3` asserted the old silent drop and are rewritten as `test_ramp_of_zero_duration_raises` and `test_a_flat_ramp_is_kept`.

The diagnosis follows.

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

### A4 — `origin.auto` falls through to an implicit `None`, and `ramp` walks into it — **RESOLVED AND FIXED 2026-09-18**

**RESOLVED AND FIXED 2026-09-18.** The maintainer chose the second of the two options: fall back, not raise. `auto`'s time default is now a **terminal chain**, and `ramp` owns `config.ORIGIN__DEFAULTS__RAMP = [["anchor", "variable"], ["last", "variable"]]` -- the `"last"` step it never had. Where nothing in the chain is satisfiable the time origin is `0.0` **with a warning**, so `auto` can no longer return `None` implicitly. NEW-9 goes with it: an explicit `origin="anchor"` on an anchorless timeline now raises a message naming the missing anchor rather than `anchor is an unsupported option`, while the *default* path falls through the chain as documented -- the two paths now differ deliberately rather than accidentally.

The diagnosis follows.


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

### A5 — `stack` turns an unrecognised keyword into a phantom variable — **RESOLVED AND FIXED 2026-09-19**

**Unblocked by C1**, which was settled on 2026-09-16, and fixed here on the rule the maintainer approved: a keyword forwarded by `stack` must be **declared as a named parameter** by at least one constituent. Not "accepted by" — every core function takes `**vtvc_dict`, so "accepted" is true of everything and would leave the defect exactly where it was.

The implementation cost this entry predicted was real and is paid: a constituent is an opaque closure by the time `stack` sees it, so each now records what its chain can consume (`util.ATTRIBUTE__KEYWORDS`) — `function__lambda` from the wrapped function's signature, `stack` as the union over its own constituents, which is what makes a nested stage answer for the stages inside it.

The subtlety worth keeping: a constituent that records nothing is **neutral**, not permissive. `noop` absorbs any keyword and does nothing with it, so treating it as permissive would switch the guard off for every stack containing one — and the lab's conditional stages put one in constantly. Neutral means it neither vouches for a keyword nor objects to it, so `stack(base, update(...), noop, typo=3.0)` still raises.

Where *no* constituent records a set there is nothing to check against and the guard stays off, which keeps a hand-written `lambda tline: ...` usable.

Covered by `test/wigner/time/timeline/test_forwarded_keywords.py`. The diagnosis follows.

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

### A6 — an interwoven `ramp` silently loses its value origin and starts from zero — **RESOLVED AND FIXED 2026-09-18**

**RESOLVED AND FIXED 2026-09-18**, by the fix direction below: `auto` completes a partial origin **per slot** rather than replacing it wholesale. The vocabulary change that makes this coherent is that **`None` in a slot now means *defer to the default for this slot*, and `0.0` means *absolute***; previously `None` meant absolute, which is precisely why a bare context name cancelled `ramp`'s value default. Measured after the change: `ramp(..., origin="stage1")` starts from 2.0, the value the variable held in `stage1`, and agrees with `origin=["stage1", "variable"]` exactly. B2 was settled in the same commit, as required.

**One user-visible consequence, for the record.** Completion gives `ramp` a value origin in cases that previously had none, so a ramp of a variable with **no previous value** now refuses where `origin=0.0` used to start it silently at 0.0. Verified against `fba0fe0`:

```
before:  tl.ramp(base, fresh__A=5.0, duration=0.5, origin=0.0)  ->  [[0.0, 0.0], [0.5, 5.0]]
after:   the same call                                          ->  ValueError, naming fresh__A
```

Zero on an uninitialised coil or lockbox is a command, not a neutral default, so refusing is the better answer — and both ways of saying what was meant are explicit and unchanged: `origin=[None, 0.0]`, or the 2-D form stating both ends. The default-origin path already refused before, just with `fresh__A is an unsupported option for 'origin'`. Pinned by `test_origin_defaults.py`.

The diagnosis follows.


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

### A7 — `"last"` and `"anchor"` are accepted as VALUE origins, where they are category errors — **RESOLVED AND FIXED 2026-09-18**

**The maintainer opened both gates on 2026-09-18**: the `fig:origin` caption is defective here, so §G does not apply and the narrowing was carried out in full — `"anchor"`, `"last"` *and* context names now raise in the value slot. The caption and `sec:origin_full` were amended to state the split, and `_ORIGINS__TIME` / `_ORIGINS__VALUE` in `internal/origin.py` are now the vocabularies `find` dispatches on. `_to_col_var` takes a `slot` argument; the one-label-for-both-slots case (`[s, s]`) is validated against the stricter of the two.

**The figure followed on 2026-09-19** (#123): `graphic/origin-resolution.pdf`, drawn per slot, generated by `graphic/origin_resolution_figure.py` rather than exported from a mind-mapping tool — so the next change to the mechanism is a rerun, not a redraw. The PNG it replaces is still in the tree, unreferenced.

Covered by `test/wigner/time/internal/test_origin_slots.py`. The diagnosis follows.

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

### A8 — a value origin is added on top of an explicitly stated `ramp` start value — **RESOLVED AND FIXED 2026-09-18**

`ramp`'s value origin defaults to `"variable"`, and `_update_future` applies it **additively**. That is right for a variable whose start point was inferred, but it is applied just as readily to a start value the user stated explicitly in the 2-D input form.

```python
# coil__A last known at 7.0
tl.ramp(timeline=base, coil__A=[[0.0, 1.0], [0.5, 3.0]])
# start value comes out as 8.0 (= 1.0 + 7.0), not the 1.0 that was written
```

`tab:rampExamples` documents that exact form as "for cases where the start cannot be inferred from `origin`" — i.e. the user is overriding the inference — so adding the inferred value back on top defeats the only reason to use the form.

Fix direction: resolve the value origin only for variables in `df__no_start_points`, never for those in `df_1`. Settle together with B1 and A3, which sit in the same block of `ramp`.

**RESOLVED AND FIXED 2026-09-18**, by the fix direction above.

The exemption was first implemented, then backed out the same day on the grounds that it removed an idiom `test_ramp_combined` relied on — "hold at the current value for 5 s, then ramp", written with a stated start of `0.0` used as an *offset*. **That reasoning was wrong, and the maintainer spotted why**: the test dates from 2025-03 (`2927057`) and is a translation of the `wait` mechanism that the origin machinery replaced. The 2-D form was never needed for it. All of these were measured equal on 2026-09-18:

```python
base = tl._populate_timeline("lockbox_MOT__V", [[1.0, 1.0]], context="badger")

tl.ramp(base, lockbox_MOT__V=[[5.0, 0.0], [1.0, 10.0]],
        origin=["lockbox_MOT__V", "lockbox_MOT__V"], origin2=["variable"])  # the test, 2025
tl.ramp(base, lockbox_MOT__V=[[5.0, 0.0], [1.0, 10.0]], origin=["lockbox_MOT__V", "variable"])
tl.ramp(base, lockbox_MOT__V=10.0, t=5.0, duration=1.0)                        # idiomatic
tl.ramp(base, lockbox_MOT__V=10.0, t=5.0, duration=1.0, origin=["last", "variable"])

# all -> [[6.0, 1.0], [7.0, 10.0]]
```

`t` places the start point and the default origin supplies its value, which is exactly what "drop a ramp in at this moment, from wherever the variable is" means. So the 2-D form carries no second job, `tab:rampExamples` is honoured literally, and the exemption costs nothing.

The test is rewritten to the idiomatic spelling, and `test_ramp_start_stated_explicitly` now pins the behaviour the issue is about: with `lockbox_MOT__V` sitting at 0.2, a ramp written from 0.0 starts at 0.0.

### A9 — reserved origin words silently shadow real context and variable names — **RESOLVED AND FIXED 2026-09-18**

`_ORIGINS` is now derived from `_ORIGINS__TIME`, so there is one list rather than two that can drift, and `timeline._populate_timeline` refuses a `variable` or a `context` named after one of them — at the point the name is written, not where it later fails to resolve, because by then the timeline no longer records that anything else was meant. The diagnosis follows.

`_to_col_var` tests `"anchor"`, then `"last"`, then variable names, then context names. So a context or variable actually named `anchor`, `last` or `variable` is unreachable as an origin, silently. Verified with a context literally named `anchor` whose rows sit at t=1, alongside a real anchor at t=5: `origin="anchor"` resolves to **5.0**, not 1.0.

`_ORIGINS = ["anchor", "last", "variable"]` exists in `origin.py`, with a docstring saying these labels are reserved for interpretation by the package — and is referenced nowhere in it.

Fix direction: make `_ORIGINS` the single source of truth, and reject a context or variable name that shadows one at the point it is created. `connection.new` already validates variable names; contexts are unvalidated. A collision is a mistake in the client's vocabulary, so raising at creation beats resolving it silently either way.

### A10 — `create` silently corrupts a positional row of more than two elements — **FIXED 2026-09-17**

The row form read only its second element and discarded the rest, so `["v", time, value, context]` produced the *time* as its value and lost the context entirely. Every value collapsed and every context vanished, with no warning. GitHub issue #58, open since 2025-03-24.

**The fix was already present in the sibling branch.** `convert`'s flat case has always read

```python
__ensure_time_context(vtvc[1]) if len(vtvc) == 2 else __ensure_time_context(vtvc[1:])
```

while `__correct_variable_list` did only the first half. Applying the same rule per row makes the two forms one grammar: `["v", t, value, context]` is `["v", [t, value, context]]` with the brackets dropped, exactly as `create("v", t, value, context)` already allowed. Two lines; no new syntax.

Verified that the nested and keyword forms now produce identical frames, and that the issue's own example parses as written.

### A11 — mixing positional and keyword input silently discards the keywords — **FIXED 2026-09-17**

`convert` read `**vtvc_dict` only when there were no positional arguments, so `tl.create(["a_b__V", 1.0], c_d__V=2.0)` dropped `c_d__V` entirely, with no error. Worse in kind than A10: that produces a visibly wrong row, this produces no row at all, so the variable is simply absent from the experiment and reads later as a deliberate omission.

**Fixed by raising**, naming the keywords that would have been lost. No merge is sensible: the two forms each carry their own `t`/`context` handling, and the keyword namespace is deliberately open (`sec:forwarding`), so a dropped keyword cannot be told from an intended variable.

Tracked as [#132](https://github.com/WignerQuantumOptics/Wigner_Time/issues/132).

---

### A13 — `ramp` silently discards a third point **[new, found 2026-09-20]** — **FIXED 2026-09-20**

Found while examining B6 at the maintainer's prompting. `ramp`'s 2-D branch reads `v[0]` and `v[1]` and never looks further, so a variable given three points became a ramp between the first two:

```python
tl.ramp(base, c__A=[[0.0, 1.0], [0.5, 5.0], [1.0, 9.0]])
#  1.0  1.0
#  1.5  5.0      <- the third point silently discarded
```

The `case _:` guard only fires for `ndim > 2`, so a *longer* list of pairs is not deep enough to reach it. **`ramp`'s own docstring asserts the opposite**: "Supplying a different number of points will result in an error."

This is A10's defect — `create` reading a positional row of more than two elements and dropping the rest — in the one function that sweep did not reach. Fixed the same way: the count is checked against what the interpolating function takes, and the refusal names the variable, its count, and the function's.

---

### A12 — a negative ramp duration silently swaps the ramp's endpoints — **RESOLVED AND FIXED 2026-09-18**

Raised by the maintainer while reviewing the A3 guard: *what happens when a ramp's duration is negative?*

Nothing refused it, and the result was not merely a ramp in the wrong place. `timeline.expand` sorts each ramp's rows with `sort_values(by=["variable", "time"])` before pairing them, so a backwards ramp had its start and end **exchanged**. Measured on `bb55695`, with `c__A` sitting at 4.0 and an anchor at t=8.0:

```python
tl.ramp(base, c__A=9.0, duration=1.0)
#   ramp 4.0 -> 9.0 over t = 8.0 .. 9.0        final value 9.0
tl.ramp(base, c__A=9.0, duration=-1.0)
#   ramp 9.0 -> 4.0 over t = 7.0 .. 8.0        final value 4.0
```

So a sign slip in a computed duration left the variable **at its old value rather than at the target**, and laid the transition across the second *preceding* the origin, on top of whatever was already there. Nothing warned, and the resulting timeline is internally consistent, so it would have run.

`internal/util.range__inclusive` compounds it: its `np.abs(... + 1)` makes the point count meaningless for a negative interval — `ri(5.0, 4.0, 0.2)` gives 4 points at a spacing of 0.333, and `ri(5.0, 4.5, 0.2)` gives a single point. Moot once the case raises, but worth knowing if that function is ever used elsewhere.

**FIXED 2026-09-18**, alongside A3 and by the same reasoning: the guard tests the signed duration rather than its magnitude, so zero and negative are refused together, each listed separately in the message. Pinned by `test_ramp_of_negative_duration_raises`.

---

### A14 — a mistyped device name silently disables that device's safety limits — **RESOLVED AND FIXED 2026-09-21**

**Maintainer's decision: both directions raise** — "it has to be both ways for it to make real sense". `device.check_correspondence(connections, devices)` is called from `adwin.internal.add`, which is where the two tables meet and where hardware enters. `device.new` also validates the name shape now, as parity with `connection.new`, and its bare `except:` is narrowed so that the name check can be seen at all.

**The check found two inconsistencies in our own fixtures**, which is the argument for it:

- `test_adwin.test_convert` declared a device for `lockbox_MOT__V` where the connection and the timeline both used `lockbox_MOT__MHz`. Orphaned, and nothing had noticed.
- `_digital_only()` declared `coil_unused__A` — the name says it was never meant to correspond to anything. It was standing in for "a devices table with no analogue channels", which turned out to be inexpressible: `device.new()` raised. A purely digital apparatus is a legitimate description, so it now returns an empty table.

Demo and lab timelines hash identically and `convert` produces the same 8261 analogue and 35 digital tuples, which is expected: the correspondence was already exactly 1:1 in both. Covered by `test_device.py`.

`device.new` validates nothing about the variable name — neither that it is well formed, nor that anything else refers to it. `connection.new` does the first; `device.new` does neither. Raised by the maintainer as something previously tracked; it was not, here or on the tracker. D7 notes in passing that names are "enforced by `config.VARIABLE__REGEX` and by `connection.new`", which is the closest anything came to recording the asymmetry.

The tidiness half is that `device.new(["notavariable", 1.0, -1, 1])` is accepted where `adcon.new` refuses it. The dangerous half is a **correctly-shaped name that refers to nothing**:

```python
connections = adcon.new(["coil_MOT__A", 4, 1])
devices     = device.new(["coil_MOTT__A", 2.0, -5.0, 5.0])   # one transposed letter
timeline    = tl.create(coil_MOT__A=500.0, t=0.0, context="s")

device.check_within_range(device.add(timeline, devices))
#  -> passes. 500 A accepted on a coil declared +/-5 A.
```

The device row joins to nothing, the variable arrives with no bounds, and `check_within_range` reads absent bounds as "no device entry — a digital line, typically — and is skipped". The stated purpose of `value__min`/`value__max` is error-checking before values reach real devices, and one transposed letter turns it off in silence.

**Validating the shape is not enough**, because `coil_MOTT__A` is well formed. Two checks are wanted: shape, in `device.new`, as parity with `connection.new`; and *correspondence*, somewhere that sees both tables — `adwin/internal.add` or `adwin.core.convert`, the one point hardware enters.

**The correspondence check is viable.** Measured across both repositories, the relation is exactly 1:1 and nothing enforces it:

```
demo: 9 analogue connections, 9 devices   lab: 8 analogue connections, 8 devices
   analogue but no device  : none            analogue but no device  : none
   device but no connection: none            device but no connection: none
```

**The decision in it**, and the reason this is not simply fixed: an analogue variable with a connection but no device has neither calibration nor limits on a channel that will be driven — recommend raising. A device with no connection is dead weight and almost certainly a typo, but harmless in itself, and one could legitimately keep calibrations for hardware not currently wired. It is nevertheless the half that catches the transposition above. What has to be settled is whether "digital line" remains the only licensed reason for a variable to reach the hardware unbounded.

Note also that `device.new` wraps its frame construction in a bare `except:` which discards the cause and re-raises `"=== Input to 'device' not well formatted ==="`. That is the pattern §"loud and early" forbids, and it would swallow whatever the name validation reports unless narrowed first — the same fault fixed in `adwin/connection.py` on 2026-09-11.

Tracked as [#141](https://github.com/WignerQuantumOptics/Wigner_Time/issues/141).

### A15 — an upload can land under a run that is still playing **[new, found 2026-09-23; this is #151]** — **FIXED 2026-09-24 on `issue#94` (#151, closed)**

**Fixed as proposed** (maintainer, 2026-09-24): `upload` converts first, then waits until its process reports it has stopped, and only then writes. The conversion therefore overlaps whatever is left of the previous run. When it has to wait it says so once through `wtlog`, at WARNING, the level the package's messages reach a notebook at. It waits while the status is anything but 0, so a process still in its `finish:` section is not taken for stopped. Neither the lab's scan nor the paper's listing had to change. Pinned by `test_upload_waits_for_a_running_process_before_writing`, which checks that no write precedes the stop, and `test_upload_to_a_stopped_process_neither_waits_nor_says_so`. **Limit:** only the process `upload` is told about is waited for. Another process playing the same arrays, such as the ADC variant, is not seen. The ownership Par of roadmap step 9 is the place to close that on the machine: a "sequence playing" flag that the sequencer itself sets and clears, rather than one process's status. **Not verified on hardware.**

The entry as found:

`adwin.core.upload` (formerly `create`) writes `Par_1..3` and the data arrays without asking whether the process is running. The machine accepts the writes mid-run, and the running sequence reads them.

The lab's parameter scan (`control/time_of_flight.py::parameter_scan_with_imaging`) and the paper's `sec:parameter_scan` listing both upload shot N+1 as soon as the camera routine for shot N returns. `take_images_ueye` returns once its frames are captured and does not wait for its own run to end. It waits for the *previous* run at its start, and by then the next upload has already been written. The lab's `finish` holds an anchor 1 s after the imaging before its final ramps and default state. So run N has a tail of more than a second, and whenever building and converting timeline N+1 takes less, the upload rewrites run N's arrays under it.

From `WignerTimeADwin.bas`: `endCC` changes, and run N's index now points into timeline N+1's rows. If the row there lies at an earlier cycle than the current count, the index never moves again, and the rest of run N is not played: its final ramps, its default state and its finish rows. If it lies later, run N plays timeline N+1's rows at run N's cycles. Nothing reports either. `createLiStore` uploads once and replays, so it is unaffected.

**Not observed.** This is from reading the lab's code and the backend; whether it bites depends on how long the conversion takes against the tail. Fix direction (roadmap step 6 at #94, for the maintainer): `upload` waits for its process to stop before writing. It is the only path to the machine, so that covers the lab's scans and the paper's listing without changing either.

---

## B. Correctness

### B1 — `ramp`'s degenerate-row check aligns on index, not on variable — **RESOLVED AND FIXED 2026-09-18**

The two boundary frames are now aligned on `variable` (`dataframe.align_to`) before being subtracted. Each holds exactly one row per variable, `df_1` and `df__no_start_points` being disjoint by construction, so the alignment is total.

**The consequence was worse than "a wrong comparison", because A3 turns it into a silent deletion.** Measured against `5d5a0cd`:

```python
base = tl.create(X__A=1.0, Y__A=5.0, t=0.0, context="s")
tl.ramp(base, X__A=[[1.0, 7.0], [2.0, 5.0]], Y__A=7.0, duration=3.0, origin=0.0)
# before: 0 rows added -- the entire ramp vanished
# after:  4 rows added
```

Nothing there is degenerate. But positionally each variable's start matches the *other*'s end in value, so every row was flagged and A3's early return discarded the whole ramp. Pinned by `test_boundary_frames_are_compared_variable_by_variable`.

The diagnosis follows.

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

### B2 — `find_every_origin` is order-dependent — **RESOLVED AND FIXED 2026-09-18**

**RESOLVED AND FIXED 2026-09-18.** `time__max__relative` is computed once, before the per-variable loop. The reproduction now gives 10.0 either way -- and 10.0 is also the physically right answer, since the ramp starts at t=5.5 and `b__A` does not step to 20.0 until t=6.0.

The diagnosis follows.


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

### B3 — `previous` sorts a filtered slice in place — **RESOLVED AND FIXED 2026-09-19**

**Superseded 2026-09-23: the sorting branch no longer exists.** It was removed with `timeline.previous` (D2, #116), having turned out to return an arbitrary row among equal times. The account below is kept as the record of the fix.

Rebound rather than sorted in place, as the fix direction said. The two branches it replaces returned the same expression anyway, so the sort is now the only thing conditional on monotonicity.

**Measured before changing it, and the severity was not quite as recorded.** On pandas 2.3.3 the answer was *correct* in both copy-on-write modes; what it did was raise `SettingWithCopyWarning` with CoW off. So this was not a wrong answer waiting to happen so much as a reliance on behaviour pandas documents as undefined — which is exactly what #88 will settle one way or the other.

The existing `sort_by` tests did not catch it because getting the right answer was never the problem; the new one asserts the caller's frame is untouched and that nothing warns.

The diagnosis follows.

`internal/origin.previous`. `tl__filtered` is a boolean-mask slice of `tline`; `tl__filtered.sort_values(sort_by, inplace=True)` on such a slice is unreliable under copy-on-write and may either warn, no-op, or write through to the parent depending on pandas version. pandas 3.x makes CoW unconditional.

**Verified 2026-09-01** (by inspection). Present as described. Reachable only through the public `timeline.previous(sort_by=...)`: `origin.find` calls `previous` without `sort_by`, so the whole `sort_values` branch is dead on the internal path. That caps today's severity, and also means it will not be caught by any test that goes through `origin`.

Fix direction: `tl__filtered = tl__filtered.sort_values(sort_by)`.

### B4 — `ramp` writes through a slice — **RESOLVED AND FIXED 2026-09-19**

`df__no_start_points` is taken with `.copy()`. What makes the write dangerous rather than merely untidy is that those rows are a **subset of `df_2`**, the frame the *end* points come from, and they are about to have their time and value overwritten to turn them into start points — so writing through would zero the very end values the ramp is aiming at.

**It did not, in either copy-on-write mode**, measured on pandas 2.3.3 before the change:

```
tl.ramp(base, c__A=9.0, duration=0.5)
  CoW off:  [[1.0, 2.0], [1.5, 9.0]]   warnings: none
  CoW on :  [[1.0, 2.0], [1.5, 9.0]]   warnings: none
```

Unlike B3, which warned. So this was fixed on the strength of the fix being one word rather than of a reproduction — "does not today" being the whole of the issue, and #88 making copy-on-write unconditional.

`test_ramp_leaves_the_timeline_it_was_given_alone` pins the invariant behind it, which nothing else did for `ramp`: no in-place modification, every core function returns a new timeline.

The diagnosis follows.

`df__no_start_points = df_2[~df_2["variable"].isin(df_1["variable"])]` is a view-or-copy, and the following `.loc[:, ["time", "value"]] = 0.0` assigns into it. Same CoW exposure as B3.

**Verified 2026-09-01** (by inspection). Present as described, but note the failure mode differs from B3's and is milder: the assignment is *intended* to modify only the local frame, which is what is passed to `concat` downstream, so writing to a copy is what the code actually wants. The exposure is a `SettingWithCopyWarning` and a dependence on pandas' copy-or-view decision, not wrong data. No such warning is emitted by the current suite on pandas 2.2. Still worth fixing — the guarantee is not one to rely on across a pandas major version — but it does not belong above B3.

Fix direction: `.copy()` at construction.

### B5 — `expand` mutates the caller's dataframe — **RESOLVED AND FIXED 2026-09-19**

Dropped into a new frame rather than in place, as the fix direction said.

**Checked first that nothing relied on the overwriting** (maintainer's instruction), and nothing does: every caller uses the return value. `adwin.core.convert` takes it as a `compose` constituent; the tests take it through `stack`; the lab never calls `expand` at all. `convert` was unharmed even so, but only by accident of pipeline order — `remove_unconnected_variables` runs first and hands `expand` a fresh frame — so `test_convert_leaves_the_timeline_it_was_given_alone` now pins that rather than leaving it to chance.

**One caller was damaged by it**, and it is the package's own: `internal/doc/demo.ipynb` expands `timeline` in one cell, expands it again in the next — silently a no-op by then, the ramps having already been removed from it — and hands `timeline` to `to_data` two cells later, by which point its ramp rows and `function` column are gone. That notebook is stale in other ways (it imports `wigner.time`, the pre-rename package), so this is evidence of intent rather than a live break.

**And a landmine worth naming.** `demo.timeline__demo` is a module-level object that the tests import. A single `expand` on it stripped it for every later user in the same process — 99 rows to 57, no `function` column. Nothing does that today; nothing stopped it either.

Measured after the change: the caller's frame is untouched, `convert` produces the same 8261 analogue and 35 digital tuples, and expanding twice now gives the same answer both times.

The diagnosis follows.

`timeline.expand` calls `timeline.drop(index=..., inplace=True)` and `timeline.drop(columns=["function"], inplace=True)` on the argument. Every other main function in this module is non-mutating and returns a new frame; `expand` breaks that contract, so a caller who keeps a reference to the pre-expansion timeline finds it corrupted.

This matters more than it looks: the "timeline as inspectable data" story depends on frames not changing under you.

Fix direction: operate on a copy.

### B6 — `expand` assumes exactly `num__bounds` rows per group — **RESOLVED AND FIXED 2026-09-20**

Fixed by removing the argument rather than by checking it. **The maintainer's observation settled the shape of this**: `num__bounds` is the number of points the interpolating function is defined by — and "bounds" is exact only for two, where start and end really are the boundaries, which is the one case in which the number need not be stated at all. A third point is an interior control point, not a bound. So the name was wrong precisely where the parameter would have earned its keep.

It also did not belong to `expand`. How many points a ramp is made of is a property of its *function*: `tanh` takes two, an interpolation with interior control points would take more. It is now declared on the function (`ramp_function.with_points`, read by `ramp_function.points`, defaulting to two so a hand-written lambda needs no ceremony) and read from the `function` column. Being derived, it can no longer disagree with the data.

Grouping is now **per variable** rather than a stride across the whole frame. The old global stride meant one variable with an odd number of rows misaligned the pairing of every variable after it; per variable the arithmetic is local and the offender has a name:

```
before:  ValueError: not enough values to unpack (expected 2, got 1)
after:   ValueError: c__A has 3 ramp row(s), which is not a whole number of
                     ramps: tanh makes each one out of 2.
```

`num__bounds` is **removed, not renamed**, and passing it raises: left in the signature's place it would have been swallowed by `**function_args` and filtered out against the ramp function's signature, so a caller still passing it would have been ignored without a word.

Verified unchanged: the demo and lab timelines hash identically, `convert` produces the same 8261 analogue and 35 digital tuples, and two ramps of one variable still expand.

`_pt_start, _pt_end = _group[["time", "value"]].values` unpacks assuming two rows. Groups are formed by `_dff.index // num__bounds` after a reset, so an odd total row count leaves a final group of one and the unpack raises a bare `ValueError` with no indication of which variable is malformed.

Fix direction: check group size explicitly and raise naming the offending variable. This becomes load-bearing if `num__bounds != 2` is ever implemented.

### B7 — a value-only origin against a variable raises a raw `TypeError` — **RESOLVED AND FIXED 2026-09-18**

**RESOLVED AND FIXED 2026-09-18.** `find` now resolves the time slot first and builds one bound from the **resolved** time -- the instant the new rows will occupy -- for both branches. `origin=[None, "variable"]` is consequently usable, and is the honest spelling of `ramp`'s own default. The related rough edge is also addressed: a variable with no history now gets a message saying so, instead of `<var> is an unsupported option for 'origin'`.

The diagnosis follows.


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

### B8 — `"last"` on an empty timeline raises an opaque pandas error — **RESOLVED AND FIXED 2026-09-18**

**RESOLVED AND FIXED 2026-09-18.** Guarded in `origin.previous`, which now names the empty timeline and points at `origin=0.0`. The default path no longer reaches it at all: `"last"` is skipped as unsatisfiable and the chain runs to its terminal `0.0`.

The diagnosis follows.


`origin="last"` resolves through `previous` to `dataframe.row_from_max_column`, which is `df.loc[df[column][::-1].idxmax()]`. On an empty frame that is `ValueError: attempt to get argmax of an empty sequence`, with nothing to connect it to origins, timelines, or the user's call.

It is reachable through the documented default, since `config.ORIGIN__DEFAULTS` falls back to `"last"` — so `update` on an empty timeline takes this path. This is the hole that a terminal `0.0` step in the default chain would close (`docs/origin-resolution.md`, suggested semantics item 3).

Fix direction: guard in `previous`, and either raise naming the timeline as empty or fall back to 0.0 with a warning, consistent with whatever the default chain decides.

---

### B9 — a ramp's sampling depends on where it sits on the time axis — **RESOLVED AND FIXED 2026-09-18**

`internal/util.range__inclusive` computed its point count as `math.ceil((stop - start) / step) + 1`. `stop - start` is a difference of *absolute* times, so it carries floating-point noise whose sign depends on the interval's position, and a bare `ceil` turns that noise into a different number of points.

Measured, for a nominally 0.8 s ramp at `time_resolution=0.2`:

```
 5.0 ->  5.8   duration 0.7999999999999998   5 points, step 0.20
10.0 -> 10.8   duration 0.8000000000000007   6 points, step 0.16
```

The endpoints and the tanh shape are right either way, so nothing looks wrong — but the effective resolution, the row count, and hence the ADwin array occupancy are not reproducible: moving a stage earlier or later silently changes the sampling of every ramp after it, and in one of the two cases the `time_resolution` that was asked for is not the one delivered.

**Found by** the A4 fix shifting a test ramp from t=5.0 to t=10.0, which changed its row count from 5 to 6. The origin change was innocent; this was underneath it all along.

**FIXED 2026-09-18** in the same commit, because an honest test of the A4 fix was not possible otherwise: the interval count is rounded first and the ceiling taken only where the quotient is genuinely not whole (`math.isclose`, `rel_tol=1e-9`). Both placements now give 5 points at step 0.2, and no other row count in the suite, the demo or the lab changed.

---

### B10 — `stack` cannot forward a keyword into a nested stage **[new, found 2026-09-19]**

`stack` wraps each constituent as `lambda x, f=f: f(x, **kws)`, and composes them. The composed object therefore takes **only** the timeline — so when an outer `stack` forwards a keyword into it, it raises:

```python
tl.stack(base, tl.update(a__A=1.0), context="MOT")     # fine
tl.stack(base, demo.MOT(), context="MOT")              # TypeError
#   stack.<locals>.<lambda>() got an unexpected keyword argument 'context'
```

Since every user-written stage is itself a `stack`, the documented idiom works exactly one level deep. `sec:context` says "any keyword passed to `stack` is forwarded to all of its constituents … so a single `context="MOT"` labels every row that stack produces", and that is not true of a stack of stages, which is the normal case.

**Loud, not silent** — it raises, and the message names a lambda rather than the mechanism, which is the only reason it took this long to notice. **Verified pre-existing**: identical on `85d4b82`, before the A5 guard, so it is not a consequence of that work. The A5 guard passes such a call through, correctly, and it then fails here.

**Latent in practice**: neither the demo nor the lab forwards any keyword to `stack`, so nothing in either repository exercises it. That is also why the manuscript's claim has stood unchallenged.

Fix direction: replace the `funcy.compose` of single-argument wrappers with an explicit closure that threads the keywords through every constituent —

```python
def _composed(x, **kws__new):
    kws__all = {**kws, **kws__new}
    for f in constituents:
        x = f(x, **kws__all)
    return x
```

Note that `funcy.compose` cannot do this on its own: it passes one value between stages, so keywords given to the composed function reach the innermost constituent only. Since the case currently raises, nothing can depend on the present behaviour.

**Provenance.** The items below come from a review of `resources/ADwin/WignerTimeADwin.bas` carried out in a chat session (2026-09-22) alongside a rewrite of the lab's manual console, and were **re-verified here against the file as it stands** on the same date. The review's handoff document is attached to [#94](https://github.com/WignerQuantumOptics/Wigner_Time/issues/94). Two of its findings are not reproduced below, because they are already accounted for:

- its §2.2 (the scan reads past the filled region, producing a spurious `p2_dac` built from a previous run's data) **was fixed by `790528e`**, which bounded the outer test as well as the `until`. The review was reading a pre-`790528e` copy. Its proposed remedy — Python writing a terminator past the filled region — is therefore unnecessary. What remains is an out-of-bounds *read* inside the `until` if ADbasic does not short-circuit `or`; that read stays inside the allocation and its result is discarded.
- its §2.4 (one digital module hardcoded) is **D18** / [#133](https://github.com/WignerQuantumOptics/Wigner_Time/issues/133), reached independently. The agreement is worth recording: two readings of the same file, without contact, produced the same finding down to the `data_21` observation.

### B11 — an interrupted run does not restore the default state **[new, found 2026-09-22; this is #148]** — **FIXED 2026-09-25 on `issue#94`; open until verified on the rig**

**Fixed as recommended** (option 1, roadmap step 8 at #94; the maintainer's go-ahead 2026-09-25), in both `WignerTimeADwin.bas` and `WignerTimeADwinADC.bas`.
- **The final state has arrays of its own.** They are the playback numbers plus 20, without the cycle: analogue module, channel and digits in `data_31..33`, digital channel and value in `data_42..43`. The counts are in `Par_15` and `Par_16`, and each array holds `finishMaxArrayDim = 256` rows.
- **`finish:` plays them unconditionally, from index 1,** however the run ended, and no longer calls `processUpdates(2147483647)`.
- **`upload` moves the final state out of the playback arrays.** `convert`'s output is unchanged, and the Lab2 checksums with it; `upload` splits off the rows at the finish sentinel and writes them without their cycle. On the machine the sentinel therefore does no structural work any more, which was D19's structural half. In Python it still marks the final state within the converted output.
- **`upload` checks every array against its capacity** (`adwin.ROWS__MAX`, which must match the `.bas` defines), and refuses before writing anything. Nothing checked even the playback arrays before.
- **Emulated line for line.** A run stopped at cycle 150 played `-2, 100` and nothing more under the old `finish:`; under the new one it plays the final state after them. A run refused by the period check (D14/step 7) now also ends in the final state rather than the initial one.
- **Memory:** the new arrays take 5 × 256 longs, 5 KB, beside the 160 MB of `data_10..13`.

**Not verified on hardware.** Three things are believed but unchecked: that `finish:` runs when the PC stops the process, which is the premise of this entry; that a `for` loop in `finish:` is fine there; and that `Stop_Process` returns only after `finish:` has completed. Recompile both programs and load them, then stop a run midway and look at the outputs.

The entry as found:

`finish:` calls `processUpdates(2147483647)`, and the guard that gates the dispatch tests only the row at the *current* index:

```basic
if ( (analogIdx <= analogArrayDim) and (data_10[analogIdx] = cc) ) then
```

- **Normal completion.** `event:` ends through `if (cyclecount > endCC) then end`, by which point `analogIdx` has walked past every ordinary row and sits on the first `ADwin_Finish` row, whose cycle *is* 2147483647. The equality holds and the finish rows fire. Works.
- **`Stop_Process` during a run.** `analogIdx` is somewhere in the middle of the array, `data_10[analogIdx]` holds an ordinary cycle count, the equality fails, and **the finish rows never fire.** The process stops wherever it was, leaving coils energised, shutters open and AOMs driven — whatever the timeline happened to be commanding at that instant.

The guarantee is therefore available in exactly the case where it is not needed and absent in the case it exists for. The lab's `finish()` docstring states the opposite in as many words — *"the default state will be actuated even when the process is interrupted"* — so this is a documented promise the backend does not keep, and `CONTEXTS__SPECIAL`'s `ADwin_Finish` is the frontend half of the same promise.

**The paper makes the promise too**, twice: `sec:context` (main.tex:682) says the reserved contexts mark rows actuated "on termination including interruption – so that the apparatus is left in a defined state however the run ends", and the appendix listing of `finish` (main.tex:1136) reproduces the lab's docstring. So this is `paper-affecting`, and by §G the backend changes, not the text (noted 2026-09-23, #94).

**This is the item to settle before the package is public**, and not for tidiness: aborting a run is the ordinary response to something going wrong, which is exactly when an apparatus should not be left driven. It is the one entry in this document whose failure mode is physical rather than numerical.

Not a *silent* failure in this document's sense — nothing returns a wrong answer — but it outranks either category, because the operator has an explicit reason to believe the opposite of what happens.

Fix direction from the review, **not approved, and a §C decision because it changes the Python/ADwin array contract**: stop reusing the playback arrays for teardown. Put the finish rows in arrays of their own (`data_30..33`; a few hundred entries suffice), applied unconditionally from index 1 in `Finish:`. The playback path then has no special final case, and the sentinel cycle 2147483647 stops doing structural work, which also relieves D19.

The cheaper alternative — have `Finish:` scan forward for the sentinel before dispatching — keeps the contract but adds an unbounded loop to the teardown path and leaves the sentinel load-bearing. Recorded as the fallback, not the recommendation.

**Not verified on hardware** (§E). The reasoning is from the source and from the cycle numbers Python emits.

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

### C3 — `anchor` with `t=None` — **RESOLVED AND FIXED 2026-09-17 (`t` is required)**

The docstring carried an unresolved TODO asking what happens when `t` is unspecified, with the author's own guess that it fails. It did, with `ValueError: Badly formatted input to __ensure_time_context` — a message naming a private function and not the argument.

**`t` is now required**, which is the signature `sec:anchor` documents (`def anchor( t, timeline=None, context=None, origin=None )`), so this is a D7 reconciliation needing no manuscript change to the signature itself. `anchor(None)` raises a message naming `t` and showing the idioms.

**Why no default is possible, which is the substance of the item.** `t` is a displacement from whatever the `origin` resolves to, and the two candidate readings are genuinely different instants:

```
anchor(0.0)                  # at the most recent anchor
anchor(0.0, origin="last")   # at the last entry in the timeline
```

They coincide until a stage writes rows past its own closing anchor — and then they do not. Measured on the shipped demo: identical through `MOT`, `MOT__detuned_growth` and `molasses`, then **0.0999 s apart from `optical_pumping` onwards**, which reinitialises its shutters 0.1 s after its anchor.

That divergence is also the argument against the other candidate, which was to keep `t=0.0` *and* change `anchor`'s default origin to `"last"`. That is self-consistent — `anchor()` and `anchor(0.0)` would agree — but it changes the meaning of every existing `anchor(duration)` call, and in the demo it would move the start of `magnetic_trapping` by ~0.1 s. Anchor-chaining is what makes each stage's `t` a Δt from the end of the *preceding stage* rather than from whatever row happened to be written last, which is exactly what lets `optical_pumping` reach past its own anchor without dragging its successor along.

`sec:anchor` now states that `t` is required, that it is a displacement rather than an absolute time, and gives both idioms with the demo's ~0.1 s divergence as the reason to state the intent at the call site.

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

### C5 — settle and document the whole `*vtvc` / `**vtvc_dict` input grammar — **RESOLVED AND FIXED 2026-09-17**

Settled in two steps. First, the grammar was never really two grammars: the flat positional form already allowed `create("v", t, value, context)` and the row form was simply missing the same rule, which is all A10 was. Applying it made the forms agree.

Then the positional forms were withdrawn from the public surface altogether (2026-09-17). Nothing needed them: `**{...}` expresses everything they do, including `expand`'s own row and names computed at runtime — and names that are not valid Python identifiers, which is how `anchor` already writes its `⚓_001` row. `expand` was the only non-test caller. So `create` takes keywords only:

    create(AOM_MOT=<follows>)

with `<follows>` being `value` \| `[time, value]` \| `[time, value, context]` \| a list of those, and `t`/`context` as **defaults, not overrides**. The positional forms remain on the internal `_populate_timeline`, where rows are assembled rather than named.

The reason to withdraw rather than keep them is the open namespace: the keyword namespace *is* the variable namespace (`sec:forwarding`), so an unrecognised keyword is read as a variable rather than rejected. A parallel positional syntax is then a second thing for that to be confused with — and it carried the one genuinely hard-to-read corner, the arity-overloaded `create("v", 9.0)` against `create("v", 9.0, 1.0)`.

The ambiguity this entry called "genuine" was not. `create("v", 9.0)` against `create("v", 9.0, 1.0)` is arity overloading — decidable, and no worse than `range(stop)` against `range(start, stop)`. The real defect was the silent truncation of row-form elements past the second (A10), plus A11, found while mapping this.

Five changes: the row rule (A10); mixing the forms raises (A11); `[]`, a bare name, over-long rows and over-nested values raise messages naming what arrived rather than citing the private `__ensure_time_context`; a non-numeric value is rejected before it reaches `astype`, where it used to surface as `TypeError: float() argument must be a string or a real number, not 'dict'` from inside pandas; and the grammar is documented in `create`'s docstring.

**Manuscript updated** (the `paper-affecting` half): `sec:functions` gives the signature without `*vtvc`, says why a variable is always named as a keyword, and `tab:inputSpecs`'s caption no longer advertises the positional forms as available for programmatic use — it now says the package uses them internally when expanding a ramp. The grammar itself is in `create`'s docstring, which is what `docs/api.md` publishes through mkdocstrings and what the caption defers to.

`test_input_grammar.py` covers it, including the totality property this entry asked for: across a spread of generated shapes, each either produces a frame with the documented columns or raises `ValueError`. That test is what found the non-numeric hole.

**Blast radius was nil.** `expand`, the only programmatic producer, passes a two-element row (`[name, (N,2) array]`), untouched by any of it; demo and lab use the keyword form throughout; the one test using a long row had it commented out because it was broken.

### C6 — a `context` given to `stack` silently skips a leading timeline **[new, found 2026-09-23; open; this is #145]**

`stack` forwards its keywords to the stages it composes, and a stage has to be a deferred function to receive them. A leading argument that is already a timeline receives nothing. `create` always returns a timeline (C2), so in

```python
stack(create(AOM_MOT=1, shutter_MOT=0, t=0.0), anchor(0.0), context="initialization")
```

only the anchor is in `"initialization"`; the `create` rows have an empty context. That was the paper's own `init` listing in `sec:stacking` until 2026-09-23 (the listing now gives the context to `create`).

**With a reserved context the result is a different hardware sequence, silently.** Measured with the demo's connections: `stack(create(AOM_MOT=1, shutter_MOT=0, t=-1e-6), anchor(0.0), context="ADwin_LowInit")` leaves both variables outside `ADwin_LowInit`. `adwin.core.convert` accepts it without complaint and writes them at **cycle 0** of the run, not at the low-initialisation sentinel. So the initial state is set as the run starts rather than before it. The demo and the lab are not exposed: their `init` passes the context to `create` through `default_state`.

**Applying the context to the leading timeline is not an option.** The idiom `sec:stacking` teaches is `stack(timeline, update(...), ramp(...), context="MOT")`, where `timeline` is everything built so far and must keep its contexts. `stack` cannot tell that from a fresh `create(...)`.

Options:

1. **Raise in `stack`** when `context=` is given and the leading timeline has rows with no context, naming the fix (give the context to `create`). Loud at the point of ambiguity, and an established timeline passes untouched. The open detail is the trigger: *any* context-less row would also fire on every later `stack` over a timeline that began with a context-less `create`, so it may have to be "no row has a context" instead.
2. **Make `create` require a context**, so that no row is ever context-less and the case cannot arise. Stronger, and consistent with the paper: every `create` it shows passes one (`main.tex:452`, and each row of the table at `:550`–`:557`). The lab is not affected: its one direct `create` (`control/camera_control.py`) already passes `context="ADwin_LowInit"`. About 16 `create` calls in the suite would need one.
3. **Document it** in `sec:stacking`. Listed for completeness; by §G, a rule that needs this qualification is a signal to change the code.

**Two findings of 2026-09-25, made while exploring #85, and how that settles the item.**

- **A forwarded `context` also *overrides* one the constituent states itself.** `util.function__lambda`'s closure merges the forwarded keywords last, over the ones the call was made with. Measured:

  ```python
  tl.stack(base, tl.update(a_b=1, context="ADwin_Finish"), tl.anchor(1.0), context="finalRamps")
  # a_b lands in finalRamps
  ```

  With a reserved context that is the same change of hardware sequence as the skip above, in the other direction. Neither the demo nor the lab combines the two, so nothing is exposed today. It matters for #85: once `init` is a constituent, `stack(init(), ..., context="experiment")` replaces `ADwin_LowInit` in the same way (measured on the C7 prototype). Resolving the skip without this would only mirror it. **Settled with #85 (C7, item 4): a keyword forwarded by `stack` is a default, not an override** — the rule `t` and `context` already follow in `create`'s input (C5).
- **The skip itself disappears with #85**, because nothing but stages enters a `stack`. **Option 2 then follows without being imposed**: the first rows of a timeline have nothing to inherit a context from, so they must name one. `update` onto an empty table already refuses — but with the wrong reason: `Nothing to resolve against: the timeline is empty ... give a number instead -- origin=0.0`, and following that advice gives the same error, since what is missing is the context (`inherit.context` calls `origin.previous` on the empty table). Under #85 that is the first error every user who forgets a context meets, so the message has to name the context.

Depends on #85 and, through it, on B10 (#136).

### C7 — composition takes stages only, and one function turns a stage into a table **[#85; direction settled 2026-09-25; the name and two details open]**

**The question, as Thomas meant it** (maintainer, reopening #85 on 2026-09-25): not whether to rename `create`, but whether `stack` and `cascade` should compose *stages* only — functions of a timeline — and never a timeline. `create` then has nothing left to set it apart from `update`, and a separate step turns a composition into a table. Thomas's own words on #145: "Just always `stack` functions and then resolve them when needed?"

**Settled by the maintainer, 2026-09-25:**

1. **All the way, not only `stack` and `cascade`.** Stages and the core functions stop taking `timeline=` as well. Stopping at `stack`/`cascade` would break the stage convention regardless — `MOT(timeline=t)` hands a table to its own `stack` — and would keep `update(timeline=...)` as a second way to the same place.
2. **`create` is deleted, not redefined.** On an empty table `update` already does what `create` does: the origin falls back to zero and the context must be stated. Redefining `create` as `update(origin=0.0)` was the alternative, and is a silent hazard: written after an anchor at 5.0, such a row lands at 0.0, before everything it was written to follow — A4's failure, by construction.
3. **The fallback warning goes** (A4's terminal `0.0`). Every experiment now starts from an empty table, so it would fire once per experiment and tell nobody anything.
4. **A keyword forwarded by `stack` is a default, not an override.** Without this the change turns C6 into its mirror image; see C6.
5. **The bridge is a plain function**, `f(stage, onto=None)`: the stage applied to `onto`, or to an empty table. Not a marker placed inside `stack`, which would make `stack` return a table or a function depending on its arguments again — Thomas's complaint on #145. `resolve` is ruled out as its name, because origin resolution already owns the word (`docs/origin-resolution.md`, `fig:origin`).

**Open:**

- **the name.** `to_timeline` (the issue's title) and `seed`, after crystallization (maintainer, 2026-09-25), are proposed;
- **whether `expand` stays usable inside a `stack`.** It has the dual form today, so `expand(time_resolution=...)` can sit in one. Unlike `update`, `ramp` and `anchor`, which add rows, it transforms the whole timeline it receives, and that is the trap recorded in CLAUDE.md: mid-`stack` it expands every ramp so far and drops `function`, so the `expand` inside `convert` becomes a no-op. No stage in the demo, the lab or its notebooks uses it that way — three tests do — and `convert` composes it as a plain table function. The recommendation is that `expand` take a table only, like `convert` and the display, which removes the trap rather than documenting it;
- **what time a row in a special context should carry.** Raised by the maintainer against item 3: `ADwin_LowInit` has to be given a fictional negative time, which makes it awkward to program. Being explored.

**Prerequisite: B10 (#136).** `init()` becomes a stack, and a `context` forwarded into a nested stack raises today.

**Measured on a prototype built over the current package** (scratchpad, nothing committed): the bridge as `f(onto or an empty table)`, and `create` replaced by `update`.

- The demo's `cascade` gives `timeline__demo` exactly, all 99 rows.
- The lab's `prepare_sample`, rewritten as a list of stages cut at `stage` instead of threading `timeline=` by hand (L6 there), gives today's table in all 20 cases: 5 stages × finish on/off × dispenser on/off.
- `imaging_absorption` interwoven gives the same table onto a finished timeline and as a later stage of the same stack.
- C6's own example puts every row in `ADwin_LowInit`.

**What it removes from the manuscript** are the sentences that exist to qualify the present behaviour: `main.tex:727` (`MOT` takes a timeline and passes it to its first constituent), `:749` (why `init`'s stack evaluates immediately), `:773` (what `cascade` returns depends on its first stage) and `:864` (`create` and `update` distinguished only by how they compose). That is §G's signal, read the right way round. `default_state` loses `f=tl.create`/`f=tl.update`, which brings `:892` ("differing only in an argument, `MOT_ON`") closer to true. 22 stage signatures lose `timeline=None`: 8 in the demo, 14 in the lab.

**Blast radius.** Package: `timeline.py`, `util.ensure_timeline`'s messages, the demo. Tests: 12 files, about 56 calls handing a table to a core function and 31 stacks led by a table, `create` or `init`. Lab: `prepare_sample`, 7 stages in `diagnostics.py`, a line each in `time_of_flight.py` and `camera_control.py`, 14 interweaving calls in `diagnosticsStageByStage.ipynb`. Untouched: the ADwin backend, and the Lab2 fixture, which is a frozen table. Manuscript: nearly every listing, which is why #85 moved to `10 — paper` on 2026-09-25; best done in one pass with D7 (#121), which rewrites the same listings.

**Folded in:** the non-running opening listing of `sec:definitions` (see the paper items at the top), and D17's correction — under C7 a table is refused in any position of a `stack`, with a message naming the bridge.

---

## D. Structural

### D1 — `origin.py` module identity — **RESOLVED AND FIXED 2026-09-01**

The snapshot of `internal/origin.py` imports `wignertime.internal.origin as wt_origin` and calls `wt_origin.find(...)` inside `update`, while also defining a module-level `find`. This is either a module importing itself, a public shim mistaken for the internal module, or genuine duplication.

**Finding: the first of the three. A module importing itself.** There is exactly one `origin.py` in `src/` (`src/wignertime/internal/origin.py`); there is no public shim and no duplication. The self-import is legal — the module object is already in `sys.modules` by the time the statement executes — and `wt_origin.find` resolved to the same function object as the module-level `find`. So the module map is the obvious one, and no inference elsewhere in this document was corrupted by it.

**Fixed.** The self-import was removed and the two call sites changed to the plain local `find`. Three lines; suite unchanged at 193 passed. Nothing else in the origins code was touched.

### D2 — `timeline.previous` is a deprecated duplicate — **SETTLED AND REMOVED 2026-09-23**

**Deleted, and `origin.previous` reduced to what the origin machinery uses** (`timeline, variable, column, time__max`; maintainer decision, #116).

*Why nothing needed it.* It had been a pure pass-through since the restructure that introduced `origin` (`8e56278`, #62), and nothing in the package called it — only four tests and some untracked notebook checkpoints, all doing `tl.previous(timeline, "coil_MOTlower__A")` to read where a variable stood before writing the next step by hand. That is the lookup the origin vocabulary now states declaratively (a variable name, `"variable"`, `"last"`, `"anchor"`, a context name), resolved at construction and bounded by `time__max`, which a hand-written lookup forgets. It appeared nowhere in the paper, README or `docs/index.md`. Its signature also put `time__max` and `column` in the opposite order to `origin.previous`, so a positional third argument meant different things in the two.

*Why `sort_by`/`index` went with it.* They offered "the n-th row in some ordering", and only `timeline.previous` reached them: the internal path never passed `sort_by` (as B3 recorded). With the wrapper gone they had no caller, and they were also **wrong in the one case that overlaps the default**. `sort_values` defaults to quicksort, which does not preserve the order of equal keys, so among rows sharing the latest time — every multi-variable `update` writes such rows — the sorted path returned an arbitrary row, where the default path deliberately returns the one written last. Measured on NumPy 2.4.6 / pandas 2.3.3 (AVX2): `sort_by="time"` and the default disagreed in 6/200 random timelines at 5 rows and 164/200 at 1000, and `np.argsort([4., 4., 1., 0., 2.], kind="quicksort")` already puts index 1 before 0. The ordering depends on the CPU-dispatched sort, so it could differ between machines. `time` is identical among the tied rows, so only a caller reading `value`, `variable` or `context` got a wrong answer — silently. No timeline the package builds was ever affected. `test_previousSort2` passed only because its four rows happened to come out in the right order.

A general query belongs in pandas. The tie-break the package does rely on is now tested directly (`test_previous_ties_go_to_the_row_written_last`); the B3 test went with the code it tested. Suite 337 → 334.

The original entry follows.

Marked DEPRECATED in its own docstring; delegates to `wt_origin.previous`. The comment asks whether it should be deleted in favour of the internal implementation. Decide as part of settling the public API surface, not ad hoc.

### D3 — Mutable default argument — **RESOLVED AND FIXED 2026-09-22**

`ramp(..., origin2=["variable", 0.0])` is one list object, created once at import and shared by every call for the life of the process.

**The diagnosis was right and incomplete.** It was indeed not mutated — measured: three ramps in a row leave the default equal to `["variable", 0.0]`, and neither `origin.auto`, `sanitize_origin`, `update` nor `find_every_origin` writes through it; each builds a new list. But the entry treated it as a property of `ramp`'s signature, and the exposure was not there. It was in `util.ensure_pair`, which is the package's **single** normalisation point for origins and which returned the caller's own object in one of its four cases:

```python
case [*x] if len(l) == 2:
    return l          # the argument itself
case [x]:
    return [x, None]  # a new list
case []:
    return [None, None]
```

So a two-element origin — which every stated origin and every default is — travelled through the origin machinery as an alias of whatever the caller held, while a one-element one did not. That asymmetry had no reason behind it and was the whole of the risk: any future in-place write anywhere downstream would have rewritten a *signature default*, and the failure would have been silent and durable, every later ramp in the session taking its end point from whatever the first one left behind.

**Fixed at that point rather than at the signature.** `ensure_pair` now builds a new pair in every branch, so no caller's object is retained anywhere in the origin machinery — for `origin`, `origin2`, the entries of `ORIGIN__DEFAULTS`, or any origin-shaped default added later. It also normalises a tuple to a list, which makes an immutable default a legitimate way of writing one without producing a differently-typed origin.

`ramp`'s signature is therefore **unchanged**, deliberately. `origin2=["variable", 0.0]` is what `sec:origin_full` shows and what D4 reconciled on 2026-09-20; a tuple would be the only tuple in a package that writes every origin as a `[time, value]` list, and would imply a distinction that does not exist. Changing it would have reopened a paper divergence to fix a hazard that is better removed one layer down.

**A second import-time capture, found while verifying this and fixed with it.** `origin.auto` had `origin__defaults=wt_config.ORIGIN__DEFAULTS` as a signature default, binding that object at import. `config.VARIABLE__REGEX` is documented as a rebindable default and is read on every call — the Lab2 regression fixture depends on exactly that — whereas rebinding `config.ORIGIN__DEFAULTS` would silently have had no effect on `auto`, while mutating it in place would have. Two config knobs that look alike behaving oppositely is the trap, not the aliasing.

`origin__defaults` is now **required**, in the spirit of C3: every call site in `timeline.py` already read the attribute at call time and passed it explicitly, and all four tests did too, so the default was doing nothing but holding a stale reference. Passing `None` still means "complete nothing".

Regression tests: `test_util.py::test_ensure_pair_never_returns_its_argument` (four shapes) and `::test_ensure_pair_normalises_a_tuple_to_a_list`; `test_origin_defaults.py::test_ramp_default_origin2_survives_being_used` and `::test_auto_requires_its_defaults`. **Verified non-vacuous**: reverting the one-line change fails three of them and leaves the one-element and empty cases passing, which is exactly the asymmetry described. Suite 324 → 331 passed (seven new: `ensure_pair` over four shapes, the tuple, and the two above).

**The rest of the package was then swept for the same pattern, two ways, because one instance is a bug and a habit is a design problem.**

*Statically*, by AST: every parameter carrying a mutable default, against every in-place write in its own function body — item assignment, `del`, augmented assignment, and the mutating methods of `list`/`dict`/`set`. **33 mutable defaults; 32 with no write.** The one hit, `util.function__lambda(kwargs=["vtvc_dict"])` calling `kwargs.pop(...)`, is a false positive: the name is rebound two lines earlier (`kwargs = args_in_function(...)`), so the `.pop` is on that result. The default list itself reaches only `flatten_keys`, which iterates it and never writes — and which shallow-copies its *other* argument with a comment saying why.

*Empirically*, by canary: deep-copy every mutable default and every mutable module global, run the whole suite, compare. **None of the 27 tracked objects changed across 337 tests.** (The scan also flags `__builtins__`, which is an artefact of walking module globals.)

So there is no second instance of D3 in the package. Both checks are scripts rather than tests; the argument for not making them permanent is that `ensure_pair` now removes the hazard at the point where origins — the only place the pattern concentrated — pass through, and a bespoke AST test carries a real false-positive rate, as the one above shows.

**A second and different hazard turned up in the same sweep** — a default that *names* a mutable config global rather than building a literal. Same syntax, different failure, different fix, so it is filed separately as **D23** rather than folded in here.

Tracked as [#117](https://github.com/WignerQuantumOptics/Wigner_Time/issues/117).

### D4 — Incorrect variadic annotations — **RESOLVED AND FIXED 2026-09-20**

`*fs: Callable` in both, and in `sec:stacking`, which reproduces both signatures verbatim.

**The sweep that followed found two more paper-code divergences**, in `ramp`'s listing: `origin2` was shown as `["variable"]`, which the per-slot work had changed to `["variable", 0.0]` two days earlier, and the parameter order had `t2` after `context` and `origin` rather than before. Both corrected.

All six signatures the manuscript shows — `create`, `update`, `ramp`, `anchor`, `stack`, `cascade` — now agree with the code on parameter names, order and defaults. What differs is only how each is written: the paper uses source-level forms (`wt_frame.CLASS`, `wt_ramp_function.tanh`) where `inspect.signature` renders resolved objects, and omits the `timeline` annotation on `update`. `expand` is not shown, so losing `num__bounds` (B6) left nothing to reconcile.

One thing deliberately left: a commented-out predecessor of `stack` sits just above it in `timeline.py`, carrying the same wrong annotation. It is dead, it predates the keyword forwarding and every guard, and it turns up in any grep for these annotations — but deleting a comment the maintainer may be keeping is not a fix.

`stack(timeline_or_f, *fs: list[Callable], ...)` and `cascade(*fs: list[Callable], ...)` annotate each individual argument as a *list* of callables. Should be `*fs: Callable`.

### D5 — `context_info` pandas coupling

Carries a TODO to remove the pandas dependence. Relevant to the polars-backed path; not urgent.

### D6 — `national_instruments/__init__.py` does not parse — **RESOLVED AND FIXED 2026-09-20 (maintainer)**

A missing comma between the message and `UserWarning`, so the two became one expression and the module did not parse.

Verified: it now imports and emits the intended `UserWarning`, `pyflakes` and `black` are clean on it, and `test_national_instruments.py` covers it — nothing did, which is why a placeholder nobody imports could sit broken.

One thing this did **not** do, contrary to what might be assumed: unblock the linter. `pyflakes src` reports per file, so the rest of the package was always being checked — 30 lines of output before the fix, 27 after, the difference being the syntax error itself. The 26 unused imports it lists elsewhere are pre-existing and untouched.

`src/wignertime/national_instruments/__init__.py` has a missing comma between the message and `UserWarning` in its `warnings.warn(...)` call. The module is a syntax error: `import wignertime.national_instruments` raises `SyntaxError`, and `black` cannot format the file (it is the one "cannot format" entry in a whole-repo run).

Nothing imports it, which is why the suite never noticed. But it ships in the wheel, so `pip install wigner-time` delivers a package containing an unimportable module — and the module's whole purpose is to greet an NI user with a polite "not implemented" message, which it cannot currently do.

One-character fix, no design question. Left unfixed only because it fell outside the scope of the 2026-09-01 pass.

### D7 — Settle what `__` separates, then reconcile code, labs and paper in one pass **[maintainer decision, 2026-09-02; scope reopened and sharpened 2026-09-20]**

`docs/paper/main.tex` is canonical. Where the code and the manuscript disagree, **the code changes.** This is the same direction as §G: the manuscript is not to be edited to match the code.

**Renamed 2026-09-20, because the item turned out to be a naming decision with a reconciliation attached rather than the reverse.** Two questions have to be answered before anything is renamed; the full reasoning and measurements are in the comments on [#121](https://github.com/WignerQuantumOptics/Wigner_Time/issues/121).

1. **Does `__` separate qualifiers, or only units?** The paper is not uniformly single-underscore — it writes `to__MHz` — so its rule is `__` before a unit, `_` between words. The package's is `__` before a qualifier *or* a unit. Evidence against the package's: `__` carries both meanings inside one call (`coil_MOTlower__A=0` beside `duration=duration__coil_ramp`, in `demo.molasses`); it forces camelCase inside snake_case (`lag__MOTshutter`, `AOM_OPaux`); the package applies it inconsistently anyway (`time_resolution` against `time__max`); and "is this a unit?" has an answer where "is this a qualifier?" does not. **Recommendation: units only.**

2. **Should the variable grammar become `<device>__<UID>__<unit>`?** Maintainer's proposal, with `<device>` and `<unit>` free of `_`. That last restriction is what makes it safe: measured over all 31 real names in the demo, the lab and the anchor label, **none** parses under the new grammar and all are refused, because every valid old analogue name has a `_` before its `__`. Without the restriction, every old analogue name would silently reread as *digital*. It also converts a silent misparse into a loud one for underscored devices (`power_supply_X__V` currently gives `device=power`). **Recommendation: adopt, and note that the anchor label `⚓_001` is in the refused set — `timeline.anchor` builds it as `"{}_{:03d}"` and would need `"{}__{:03d}"`.**

**Both touch the same identifiers, the same `demo/full_experiment.py` and the same manuscript listings, so they should be one pass.** `fig:timeline__example` shows variable names and regenerates from the demo. And the device field should be *consumed* by something before it is committed to — `adwin/display.py` groups by unit, and grouping by device too would exercise the distinction; a field nothing reads will drift under any spelling.

**The lab situation, from the maintainer (2026-09-20).** Lab1 is switching to pure snake_case, `__` as the unit separator only, but is stalled, so still changeable. Lab2 is greenfield. Timing therefore favours deciding now: once the manuscript is submitted the paper is fixed, and a later code change reopens the divergence permanently rather than closing it.

**Scope to settle before starting.** The paper fixes the naming of everything it *shows*; for library internals it never shows there is no paper version to reconcile to, so those are out of scope by construction. Proposed reading: reconcile the public API surface, the demo, and the ADbasic listing; leave internal identifiers (`column__value`, `timeline__past`, `mask__changed`) alone. (`num__bounds`, listed here until 2026-09-20, no longer exists — see B6.) Confirm this before renaming anything, because the alternative reading — that the paper's single-underscore style governs internals too — is a very large change.

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

### D8 — `"variable"` resolves only on one call path — **RESOLVED AND FIXED 2026-09-18**

Not by making `find` resolve it — it cannot, since `"variable"` means "whichever variable is being placed" and `find` resolves one origin for the frame as a whole. Instead `find` now says exactly that, and says where it *is* handled. `find` is testable in isolation for every origin it can meaningfully take, and the one it cannot no longer pretends to be a formatting error.

The diagnosis follows.

The literal string `"variable"` is not handled by `_to_col_var` at all. It is substituted for the actual variable name inside `origin.update`'s `find_every_origin` loop, before `find` is reached. So it works through `update`, `ramp` and `anchor`, and raises `variable is an unsupported option for 'origin'` when `origin.find` is called directly with it — even though `find` is the function whose docstring enumerates the reserved labels, and `_ORIGINS` lists `"variable"` among them.

Not user-visible today, but it means `find` cannot be tested or reused in isolation for the one origin keyword that matters most to `ramp`.

### D9 — the decision-tree figure and the config disagree on the value slot — **RESOLVED AND FIXED 2026-09-19**

The figure was redrawn as `graphic/origin-resolution.pdf`, and it is now *generated*: `graphic/origin_resolution_figure.py` writes both the PDF the manuscript includes and a PNG for looking at. That is the part worth keeping — the figure it replaces was a low-resolution export from a mind-mapping tool, so every correction to it meant reopening that tool, which is why the image and the caption had drifted apart in the first place.

Three things changed in the content: the root node reads `None` rather than `0.0`; resolution is drawn per slot rather than as one flat tree serving both (A7); and the default is shown as a terminal chain (A4). The diagnosis follows.

`graphic/origin-decision-tree-highlighted.png` (`fig:origin`) shows the default as `[["anchor", 0.0], ["last", 0.0]]`. `config.ORIGIN__DEFAULTS` is `[["anchor", None], ["last", None]]`. Numerically they agree, since a value origin of 0.0 and an absent value origin both leave values untouched, but they are different objects and only one is what the code does. **RESOLVED 2026-09-18/19.** They no longer disagree in substance: `None` now means *defer to the default for this slot* and `0.0` means *absolute*, which coincide for a value slot whose default is absolute. The redrawn figure reads `None`.

### D10 — `ensure_pair` message typo, and `find` normalises twice — **RESOLVED AND FIXED 2026-09-18**

The message now names the origin rather than the helper ("An origin is a `[time, value]` pair, so at most two"), and `find` normalises once, through `sanitize_origin`, so the timeline check does gate the early return.

The diagnosis follows.

`internal/util.ensure_pair` raises a message beginning "Two many arguments to" — "Two" for "Too". Reachable from user input: `origin=["a", "b", "c"]`.

Separately, `find` normalises the origin twice: once at the top, for the `[None, None]` early return, then again through `sanitize_origin`. Harmless, but it means `sanitize_origin`'s "timeline required for a string origin" check does not gate the early return, and a reader cannot tell which normalisation is authoritative.

### D11 — `conversion.add` is hard-wired to ±10 V / 16 bits, ignoring the per-module specification **[new, found 2026-09-12]**

`adwin/internal.py::add` takes `machine_specifications` and uses it for `modules__digital` and `add_cycle`, but calls `conv.add(dff)` with no specifications at all. The analog conversion therefore always uses `conversion.SPECIFICATIONS__DEFAULT` (`voltage_range=[-10.0, 10.0]`, `num_bits=16`, `gain=1`) and never consults `machine_specifications["modules"]`, which carries a `voltage_range` and `bits` per module precisely so that modules can differ.

Harmless on the setups tested, where every analog module is ±10 V/16-bit — which is why the demo and the lab's timelines convert correctly. But a module with any other range is silently mis-converted, with no error and no warning, and the function's own signature says otherwise. Same shape as A-class silence rather than a crash.

Found while verifying the conversion arithmetic end to end for the lab's device table.

### D12 — digital modules are identified by `bits == True` — **RESOLVED AND FIXED 2026-09-22**

`adwin/internal.py::modules__digital` selected modules with `m.get("bits", False) == True`. The digital module is declared `bits: 1` and was matched only because `1 == True` in Python.

**Be precise about what this cost, because it is less than it looks and the entry above overstated it.** `x == True` and `x == 1` are the same test for every number — there is no value on which they disagree — so the answer was never wrong, and the claim that "a module declared `bits: 2` would not be caught" is true of both spellings equally. What was wrong is that "is one bit wide" was written as a comparison against a boolean, which leaves the intent unrecoverable from the code: a reader cannot tell whether the field is a width or a flag, and the two imply different things about a module of any other width.

**Fixed as `m["bits"] == 1`, and the docstring now states the derivation** — a digital line is one bit wide, so a module of one-bit channels is a digital module.

**Why derive rather than declare.** The obvious alternative, a `kind: "digital"` field beside `bits`, was considered and rejected: it makes two sources of truth for one fact, and `{"kind": "digital", "bits": 16}` has no right answer. That is the same argument that keeps module and channel numbers out of the device conversions, and the same failure D22 describes in the console's parallel apparatus table.

**One behaviour did change.** A module declaring no `bits` at all used to fall through as analogue; it now raises, naming the offending module numbers. Reading an under-specified module as analogue is a guess about hardware, and the wrong guess puts a 16-bit conversion on a digital line. Nothing in the repository or in either lab passes a partial specification, so the blast radius is nil — verified: `SPECIFICATIONS__DEFAULT` gives every module its `bits`, and the Lab2 fixture deep-copies it and changes only `cycle_period`.

**Forward-compatible with D11.** `bits` currently has exactly *one* consumer in the package, this function, so the field's name promises a resolution while its only use is a kind test. D11's fix gives it its second consumer, as the resolution `conversion.add` should be using per module. The two readings agree — a one-bit module genuinely has one-bit resolution — so `== 1` does not have to be revisited then.

Tests in `test_adwin.py`: the shipped specification resolves to `[1]`; widths 2, 8, 16 and 32 are not digital; and an unstated width raises. **Honest about which is which**: only the last is a regression test. The others pass against the old code too — necessarily, since the old and new comparisons agree — and are pins recording the boundary the old spelling could not express. Verified by reverting: 1 failed, 5 passed.

Tracked as [#126](https://github.com/WignerQuantumOptics/Wigner_Time/issues/126).

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

### D14 — nothing cross-checks ADbasic's `Initial_Processdelay` against the cycle period **[new, found 2026-09-12; this is #128]** — **both halves done on `issue#94` (2026-09-23, 2026-09-25); open until verified on the rig**

Sharpened by D21, and half closed by the roadmap at #94: `upload` now reads the period off the machine, so Python can no longer disagree with the loaded program's header. What remains is the case D21 names, a program that sets its own `Processdelay` once started. That is the sequencer's check at the end of `init:` (step 7), a contract change still to come.

**Step 7 done, 2026-09-25**, in both `WignerTimeADwin.bas` and `WignerTimeADwinADC.bas`, so step 10 no longer has to carry it. The contract:
- **What `upload` writes.** `Par_9` (`processdelayExpected`) gets the Processdelay the arrays were built for, and `Par_14` (`processdelayReported`) is cleared to 0. Both numbers were free in all three programs; the console rewrite uses 74–78.
- **What the sequencer does.** At the end of `init:`, after anything the program may have set for itself, it writes its own `Processdelay` into `Par_14`. If that differs from `Par_9`, it sets `endCC = -1`, so the first event ends the run. The line-for-line emulation shows that only the lowinit and init rows are then played: the initial state, and nothing after it. The finish rows were not played either, because of B11; since step 8 (2026-09-25) they are, so a refused run ends in the final state. Nothing is added to `event:`.
- **What `wait` checks.** It reads `Par_14` after the run. If it is 0, the program predates the check and is refused, because nothing vouches for its run. If it differs from the upload's value, `wait` raises `PeriodRefused` with both periods in µs. The `Run` record keeps `processdelay__reported`.

**Not verified on hardware**, and needs both programs recompiled and loaded:
- That ADbasic lets a process read its own `Processdelay` as a variable is believed but UNVERIFIED; the compiler will say.
- **Until the new binaries are loaded, every run through `wait`, `running` or `run` raises "older than the period check".** This is deliberate, and it is the first thing the rig will show. A run started with a bare `Start_Process` is unaffected.

The entry as found:

`resources/ADwin/WignerTimeADwin.bas` carries `Initial_Processdelay = 5000` in its header; `adwin/internal.py` carries `cycle_period = 5e-6` seconds (renamed from `cycle_period__normal__us` by D13). These must agree, and nothing checks that they do: they live in different files, in different languages, in different units, and the Python side never reads the `.bas`.

They agree today, so this is latent. But it is exactly the pair that drifts when someone raises the Processdelay on the machine to buy resolution and does not think to change Python — and the resulting error is a *uniform rescaling of every time in the experiment*, which is a more plausible thing to misread as a physics result than as a bug. Reading the value back off the machine, or at minimum asserting it in `adwin.core.create`, would close it.

Worth noting what makes this more than pedantry: the same reasoning is why the maintainer could dismiss a suspected 5× cycle-period discrepancy immediately — a timeline that took five times as long as expected would be noticed at once. That argument protects against a *change* in the ratio, not against the two values having been inconsistent from the start, and only while someone is watching the clock.

### D15 — `adwin.core.create` silently ignores two of its own arguments **[new, found 2026-09-11]** — **FIXED 2026-09-23 on `issue#94` (#129, closed)**

**Fixed** by making the cycle period an argument rather than an entry of the specification (roadmap step 2 at #94). `convert(timeline, connections, devices, cycle_period, ...)` takes it with no default, uses it both to sample ramps (unless `time_resolution` says otherwise) and to compute cycles, and `create` passes on `cycle_period`, `machine_specifications` and `time_resolution`, printing the run length with the same period it uploads. A specification that still carries `cycle_period` is refused by `internal.specifications`: accepting it with the period unused would be this defect again, one layer down. `create` alone still assumes a period when given none, `core.CYCLE_PERIOD__ASSUMED` (5 µs), so that the paper's `adwin.create(timeline, connections, devices)` keeps running; that goes when `create` reads the period off the machine (roadmap step 5, D21). Pinned by `test_create_uploads_at_the_period_it_is_given` and `test_create_converts_against_the_specification_it_is_given`. The unconditional print is untouched, and belongs with step 5, which changes what `create` returns.

**Completed by roadmap step 5, 2026-09-23.** `create` is now `upload(timeline, connections, devices, machine, process, ...)`. The machine and the process are required, and the period is read off the machine on every call, never given, so `CYCLE_PERIOD__ASSUMED` is gone and no argument reaches the machine that could disagree with it. The print went too: `upload` returns an `Upload` log carrying the last cycle and `time__last`. The pins above were renamed `test_upload_converts_at_the_period_the_machine_reports` and `test_upload_converts_against_the_specification_it_is_given`.

The entry as found:

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

**Correction, 2026-09-25: the second consequence does not hold.** `_ensure_stackable` lets a frame through in any position, so a frame after the first still fails inside the composition with `'DataFrame' object is not callable`, naming nothing. The manuscript's opening listing runs into exactly this (`final`, main.tex:481). Not fixed here, because #85 settles it (C7): once a `stack` takes stages only, a table is refused in any position, with a message naming the bridge. #131 is left closed, since what it was filed for — the uncalled stage — is fixed.


### D18 — the backend hardcodes one digital module, the frontend models a list **[new, found 2026-09-17]**

`adwin/internal.py::modules__digital` returns a **list**, and `SPECIFICATIONS__DEFAULT["modules"]` gives every module its own `bits`, so the frontend is written as though any number of modules could be digital. Declare a second one and it agrees:

```python
spec["modules"][2] = {"bits": 1, ...}
modules__digital(spec)   # -> [1, 3]
```

The real-time program does not. Both digital calls name module 1 as a literal:

```basic
p2_digprog(1, 1111b)                                  ' lowinit
p2_digout(1, data_22[digitalIdx], data_23[digitalIdx])  ' every update
```

So every digital update, whatever module it was assigned, is written to port 1. A second digital module produces silently wrong output: rows routed to a module the hardware never receives, appearing on another instead.

The module column is not even absent from the transfer — it is sent and discarded. `core.create` writes the digital `(cycle, module, channel, digits)` tuples to `data_20..23`, but the `.bas` declares only `data_20`, `data_22` and `data_23`. **`data_21` is written to an array the real-time program never declares**, which is at best a wasted transfer and at worst an allocation the program did not ask for; which of the two cannot be determined here.

Neither half is recorded anywhere — not in this document, `CLAUDE.md`, the manuscript, or the ADbasic source. `sec:adwin`'s listing shows `p2_digout(1, ...)` without remarking on the literal.

Two ways to settle it, and they are opposites:

1. **Accept the restriction and say so.** One digital module, named in the specification rather than assumed; `connection.new` or `adwin.internal.add` rejects a digital connection on any other. `data_21` then stops being transferred. Smallest change, and it matches the hardware the package has actually run on.
2. **Honour the frontend's model.** `processUpdates` reads `data_21` and passes it to `p2_digout`. That is one more array read per digital update in the event loop, which the design spends carefully (`sec:adwin`), for a generality nothing currently needs.

(1) unless a second digital module is actually planned. Either way the present state — a frontend that accepts what the backend silently ignores — is the one option that should not persist.

**Not verified on hardware** (§E): what ADwin does with a write to an undeclared `data_21` is untested here.

### D19 — cycle-count sentinels share a namespace with the time axis, and `cyclecount` wraps into it **[new, found 2026-09-22; this is #146]** — **GUARDED 2026-09-23 on `issue#94` (#146, closed; the structural half rides on B11, #148)**

`-2` (lowinit), `-1` (init) and `2^31-1` (finish) are control-flow markers carried in the same column as ordinary cycle counts, and `cyclecount` is a `long` incremented once per executed event. Two consequences, of different weight:

- A timeline producing cycle `-1` would fire during `init:`. Unreachable from ordinary input — but note that the lab's `init()` passes `t=-1e-6`, which at a 1 µs cycle period *is* `-1`, so the Python layer is already overriding time for the special contexts, and the comment there ("time is simply a placeholder here") admits this rather than preventing it.
- `cyclecount` wraps at 2^31 — **35.8 minutes at 1 µs**, 3 hours at 5 µs — and it wraps *negative*, into sentinel territory. `if (cyclecount > endCC) then end` is then false, so the run does not stop: it continues into cycles `-2` and `-1` and replays the lowinit and init rows mid-experiment.

Beyond any real sequence today. Worth a guard on the Python side, where `adwin.core.create` already knows `time_end__cycles` and can refuse; that costs one comparison and needs no ADbasic change.

Structural rather than urgent — but B11's recommended fix removes the `2^31-1` sentinel, which is the half of this that does structural work.

**A third consequence, found 2026-09-23 and worse than either: a row before the start silences its whole array.** The arrays are sorted by cycle, so an ordinary row at cycle −3 or earlier lands *ahead of* the lowinit rows. `processUpdates` plays only the row its index points at, and only when the count equals that row's cycle. The count starts at −2 and never reaches −3, so the index never moves, and **no row of that array is played at all**: not the initial state, not the run, not the final state. Nothing raises. Reachable through the public API with nothing more exotic than `update(..., t=-1e-3, origin=0.0)`. Established by a line-for-line emulation of `WignerTimeADwin.bas` driven by `adwin.core.convert`: with the early row at +1 ms all seven rows of the digital array fire, and at −1 ms none does. **Not verified on hardware** (§E).

**Guarded on the Python side 2026-09-23, on `issue#94`** (roadmap step 3 at #94). `adwin.validate.cycles` runs first in `validate.all` and refuses any row outside the special contexts that falls outside `adwin.CYCLES__RUN = (0, 2**31 - 2)`. That covers all three consequences: collision with −1 and −2, the silenced array, and the wrap (the last playable row is 2^31 − 2, since the counter is incremented once past it). `add_cycle` now computes the column in 64 bits and `validate.types` narrows it only after the check; before, the cast to `int32` came first and would have wrapped a too-late row into a plausible-looking one. A row less than half a cycle before zero rounds to zero and is accepted. The namespace itself is unchanged, so the structural half remains, and remains B11's to relieve.

### D20 — nothing enforces the sorted-ascending invariant the backend depends on **[new, found 2026-09-22; this is #147]** — **FIXED 2026-09-23 on `issue#94` (#147, closed)**

**Fixed**, and the mechanism below corrected. `adwin.validate.ascending` checks each converted array just before `convert` returns it, and names the first row out of order, counting from 1 as the controller does. The arrays are checked, rather than the timeline, because they are the contract with the machine. The order is established by the sort in `internal.to_tuples`, and that sort, not anything upstream, is what a future change could disturb. So the check guards the only stage that can break the order.

**Correction, from emulating `processUpdates` (2026-09-23): a row out of order is played *late*, not skipped.** The inner `do … until (data[idx] > cc)` keeps playing rows until it meets one *later* than the current cycle, so a row at 200 placed after one at 300 is played at 300, together with it. The index is always left on a row later than the current count, and the count advances by one, so no ordinary row is ever passed over. The one way to stall an array is for its *first* row to lie below −2, which is D19's third consequence and is guarded there. The timing error remains silent, so the check stands.

The entry as found:

`processUpdates` advances `analogIdx` and `digitalIdx` monotonically and never rewinds, so **any row out of cycle order is silently skipped**. The invariant is real and load-bearing; it holds today by construction in `adwin/internal.py`, and is asserted nowhere. Nothing would notice if a future change to `validate.all`, to `drop_repeats`, or to the concatenation in `core.create` disturbed it.

One line in `adwin.validate`, over a column that is already materialised. That pass is also the natural home for the other static checks the review proposes (its §3.1): row counts against `Par_4`/`Par_5`, no ordinary row colliding with a sentinel, and the maximum number of rows sharing a single cycle against the per-cycle budget — the last being the event-overrun check done statically, before the hardware, rather than discovered after.

### D21 — the cycle period is stated in two places and read from neither **[sharpens D14, 2026-09-22]** — **direction settled 2026-09-23; Python half in progress on `issue#94`**

**Settled with the maintainer, 2026-09-23 (the roadmap is at #94):**

- **The period is read off the machine on every `create`**, not checked once. It is `Get_Processdelay(process) × tick(Processor_Type())`, and the tick table is the one hardware constant Python keeps. **Both labs run T12 processors, at 1 ns per tick** (maintainer). So the committed `Initial_Processdelay = 5000` is 5 µs, Lab1's rate, and Lab2 runs at 2 µs. The T11 figure below came from a review that did not know the hardware and is moot. Any other processor type is to be refused by name.
- **Read, never set.** An ADbasic program can overwrite its own `Processdelay`, so a value set from Python is not a value the machine is bound to keep (maintainer). For the same reason a read before `Start_Process` shows the value *before* any the program sets for itself when it starts. So the guarantee is completed on the machine: `create` leaves the period it built for in a Par, and the sequencer compares it with its own `Processdelay` at the end of `init:` and refuses to play on a mismatch (roadmap step 7, a contract change).
- **`convert` does not read it.** It must run without a machine (the Lab2 fixture, display, archiving), so it takes the period as an argument, with no default. Done on `issue#94` with D15.
- **Done on `issue#94`, 2026-09-23: roadmap steps 4 and 5.** `adwin.PROCESSDELAY__RATE = {"T12": 1e9}` is the table, kept as a rate so that `5000 / 1e9` is exactly the float `5e-6`, which keeps the Lab2 checksums bit-identical. `core.read_cycle_period(machine, process)` reads the period, and refuses an unknown processor, `"T12.1"` included, or a process reporting no `Processdelay`. `core.upload`, renamed from `create`, requires the machine and the process and converts at the period it reads. The Par that step 7 will compare against is not written yet: it gets its number together with the ADbasic code that reads it, rather than as half of a contract.
- **There were more copies than two.** Besides the header and the specification: `config.TIME_RESOLUTION` (1 µs, the ramp functions' default), the Lab2 fixture's 2 µs, and `#Define ClockInterval 5 ' in us` in `WignerTimeADwinADC.bas`, which turns seconds into cycles in ADbasic arithmetic (roadmap step 10). The specification's copy is gone. `TIME_RESOLUTION` no longer reaches construction: `origin.py` used it to widen the time bound on value lookups, which counted rows up to 1 µs *after* the instant as already in effect. The tolerance was removed, since setting it to zero changed no result in the suite, the Lab2 checksums included, and `test_the_bound_admits_nothing_after_the_instant` now tells the two behaviours apart. It remains only as the sampling default of `expand` outside conversion.

The entry as found:

D14 recorded that `Initial_Processdelay = 5000` in the `.bas` header and `cycle_period = 5e-6` in `adwin/internal.py` must agree, and that nothing checks it. Verified more precisely now, and the situation is worse than "unchecked":

- **Python never sets or reads the Processdelay.** There is no `Set_Processdelay` or `Get_Processdelay` anywhere in `src/`. The machine runs at whatever the deployed `.bas` was compiled with, and the package has no way to find out.
- `Initial_Processdelay = 5000` is 5 µs on a T12 (1 ns per unit) and 16.7 µs on a T11 (3.33 ns per unit). **The header is not self-describing**: the same number means different things on the two processor generations, and neither file records which is assumed.
- The manuscript quotes **1 µs** (`sec:intro`, the “Fast” paragraph, and `sec:adwin`), which is neither. So the rig is running something other than what either file in this repository states, and nothing here records what.
- **D15 closes the loop.** `adwin.core.create` accepts `machine_specifications` and does not forward it to `convert`, so a user who supplies the rig's actual cycle period has it used for the `time_end` that is *printed* and not for the `cycle` column that is *uploaded*. The one visible number agrees with the user's intent while the data does not.

So the package cannot currently be told the machine's cycle period, and the value it assumes is contradicted by its own paper. With D15 this is the most consequential item in the ADwin group: an error here is a **uniform rescaling of every time in the experiment**, which reads as physics rather than as a bug.

The remedy is the review's §3.1 check, and it is cheap, because the driver already exposes what is needed: `Get_Processdelay(1)` and `Processor_Type()` give the real cycle period, which is asserted against the specification at load and **refuses** rather than warns. That single check is worth more than the rest of the ADwin group put together, and it turns the paper's 1 µs from a quoted number into a verified one.

### D22 — the manual console is a second, divergent apparatus description **[new, found 2026-09-22; this is #94]**

The lab's manual console (`console.py` plus `ExperimentalSetupConsole.bas`, ADwin process 10) gives direct access to channels during alignment. It maintains **its own** connection table, with its own `unit_range` and `safety_range` columns, parallel to this package's `connections` and `devices`. Two parameterisations of one physical map, each maintained by hand.

They can disagree silently, and at least one pair wants checking: `coil_MOTlower__A` has `to_V = 10/5.0` over ±5 A in the lab's `devices`, and `unit_range=(-5, 5)` in the console's table. Whether those agree depends on the DAC full scale, which the review could not establish.

The harder half is that `device.new` accepts an **arbitrary callable** — the demo's `AOM_science__trans` reads a calibration file through `conversion.function_from_file` — and the console assumes a single linear map. Deriving console entries from `devices` without routing them through the same conversion path would put the wrong voltage on every calibrated channel, quietly.

Direction, from the review and **not settled**: ship the console inside the distribution as `wignertime.console` behind a `console` extra, with the `.bas` as package data; have it *consume* `connections`, `devices`, `variable` and `device.check_within_range`, and derive its ranges rather than restate them. Scope limited to the static description — the console needs no notion of a timeline, and the dependency runs one way only. Which of `unit_range` or the `device` conversion is authoritative, and how the console reaches a non-linear calibration, is a **§C decision**.

**One hazard the review introduces rather than describes, and it should not be missed.** Its console rewrite raises process 10 from `Priority = Low` to `Priority = High` (1 ms timer, ~3% duty), deliberately, so that the bounded sweep cannot be starved. But `resources/ADwin/WignerTimeADwin.bas` runs the sequence at `Priority = High` too. Under the old arrangement a running console could never preempt a sequence — the low-priority process simply got no time — so the "stop process 10 before running" rule was hygiene. Under the new one the two contend, and leaving the console running steals cycles from a microsecond-precision timeline. The rule becomes load-bearing, and **nothing enforces it**: the discipline lives in a sentence in a comment, addressed to students.

Cheap to close from Python, and it belongs there rather than in ADbasic: `adwin.core.create` can call `Process_Status(10)` and refuse to start a sequence while the console process is running. That is one call, on a path that already talks to the machine, and it converts a convention into a guarantee. It should land with the console, not after it.

**Superseded 2026-09-23: this has to be closed on the machine, not in `create`.** `create` uploads. It does not start anything: the lab calls `Start_Process` itself (`control/time_of_flight.py`, `control/camera_control.py`, the notebooks), so a check in `create` guards the upload and not the run. ADwin processes share Pars and Data arrays and can start and stop one another (maintainer). The roadmap at #94 therefore has the sequencer's `lowinit:` stop process 10, and a shared ownership Par make the console skip its writes while a run is on (step 9). That costs nothing in the event loop, and nothing a notebook does can bypass it. It still lands before, or with, the console (step 11).

Bearing on this document: once the console is in the package its defects are ours, and the review lists several of the kind catalogued here — `pd.merge` padding with `NaN` so that an `is None` test sent every digital channel down the analogue branch (A-class, and it broke precisely the path that would derive console tables from ours); `int()` truncating a DAC code toward zero instead of rounding; and `safety_range` present in the schema and read nowhere, with `unit_range` doing both jobs.

### D23 — a default that names a config global is bound at import, so rebinding it does nothing **[new, found 2026-09-22]**

**Not D3, despite looking identical.** D3 is a *mutation* hazard: a mutable default can be corrupted by an in-place write, and the fix was to stop `ensure_pair` handing back its caller's object — no signature changed. This is a *configuration* hazard: the object is never mutated, and the failure is that the supported way of changing it silently does not work. Twelve signatures, an API policy decision, and a different label. Folding the two together would have made D3's record dishonest, since the defect it names is fixed and verified.

| global | defaulted in |
| --- | --- |
| `adwin.internal.SPECIFICATIONS__DEFAULT` | `adwin.core.convert`, `adwin.core.create`, `adwin.internal.add`, `add_cycle`, `to_tuples` |
| `conversion.SPECIFICATIONS__DEFAULT` | `conversion.add`, `_add_linear`, `_add_function` |
| `adwin.CONTEXTS__SPECIAL` | `adwin.internal.add_cycle`, `adwin.validate.special_contexts` |
| `adwin.SCHEMA`, `adwin.display.SYMBOL_QUANTITY` | `adwin.validate.types`, `display.quantities` |

Each is bound at import, so **rebinding the global would silently fail to reach any of them**, while mutating it in place would reach all of them. That is the asymmetry removed from `origin.auto` above. It is currently latent rather than a broken promise: only `config.VARIABLE__REGEX` is documented as rebindable, and it is genuinely read on every call. But `machine_specifications` is exactly the thing a user has to change for their own rig (D21), and the supported route — passing it explicitly — is the one D15 says `adwin.core.create` ignores.

**Not settled here.** Making these `None`-defaulted and read at call time is a consistent policy and touches twelve signatures, so it is an API decision rather than a fix. The natural place is the single ADwin pass that D21 describes, where five of the twelve are being opened anyway.

**Interacts directly with [#142](https://github.com/WignerQuantumOptics/Wigner_Time/issues/142), which pulls the other way.** That issue asks for `origin=ORIGIN_DEFAULT` in place of `origin=None`, so that a signature shows when a default is effective. Read literally it would introduce *this* defect on the three most-used signatures in the package, and would break what the Lab2 fixture relies on — that rebinding a `config` attribute takes effect.

**Both are satisfied by one design**: the signature names an immutable **sentinel**, not the config value, and the body reads the config at call time.

```python
ORIGIN__DEFAULT = Sentinel("ORIGIN__DEFAULT")

def ramp(..., origin=ORIGIN__DEFAULT):
    if origin is ORIGIN__DEFAULT:
        origin = wt_config.ORIGIN__DEFAULTS__RAMP    # read now, not at import
```

The signature then announces that a default is effective, rebinding still works, nothing mutable is captured at import, and `None` stays free to mean what it means per slot. Measured while checking #142's second claim, that the default cannot easily be turned off — it can, but the spelling differs by function, which nothing at the call site says:

```
ramp(origin=0.0)        -> [0.0, "variable"]   # time absolute, value still from the variable
ramp(origin=[0.0, 0.0]) -> [0.0, 0.0]          # fully off
update(origin=0.0)      -> [0.0, None]         # fully off, update having no value default
```

**Recommendation, not a decision.** `None`-default and read the global inside the body, as `variable.py` already does for `config.VARIABLE__REGEX` and as `origin.auto` now does by requiring the argument outright. That is twelve signatures, five of which the D21 pass opens anyway, so the cost is mostly in the other seven.

**Counter-argument worth stating**, because it is not obviously wrong: these globals are not advertised as rebindable, and the supported route for `machine_specifications` is the parameter. On that reading the right fix is D15 — make the parameter actually work — and leaving the defaults alone is harmless. What makes it worth doing anyway is that the two knobs then behave the same way as `VARIABLE__REGEX`, which *is* advertised, and a user who finds one of them working by rebinding has no way to know the others do not.

Tracked as [#144](https://github.com/WignerQuantumOptics/Wigner_Time/issues/144).

**Applied to the first row only, 2026-09-23, on `issue#94`**, as part of the #94 roadmap the maintainer approved (step 2). `SPECIFICATIONS__DEFAULT` is now read at call time, through `adwin.internal.specifications`, by `core.convert`, `core.create`, `internal.add` and `internal.to_tuples`. `add_cycle` no longer takes the specification at all, since the only thing it read from it was the period. `add_cycle`'s `CONTEXTS__SPECIAL` default was opened by the same change and follows the same rule. The other seven signatures, and the policy question itself, are untouched and remain #144's to decide.


---

## E. Testing constraints

**A green test suite does not clear the ADwin backend.** `ADwin` is an optional extra (`[tool.poetry.extras] adwin`) and the hardware is not present in a development environment. Changes under `wignertime/adwin/` can only be checked for internal consistency; correctness must be verified on the rig. Flag any such change explicitly rather than reporting it as done.

Note that the extra being installed is *not* the same as the hardware being present: `ADwin` is a pure-Python wrapper and installs fine on a development machine, so `adwin.core` imports and its pure functions (`convert`, and everything under `adwin.internal` and `adwin.validate`) are genuinely exercised by the suite. What remains unverifiable locally is anything that talks to a device — `link_device`, and the `Set_Par`/`SetData_Long` calls in `core.create`.

~~The same applies to `conversion.function_from_file`, which reads calibration data (e.g. `resources/calibration/aom_calibration.dat`) that will not exist in a clean checkout.~~ **Withdrawn 2026-09-01: this is wrong.** `resources/calibration/aom_calibration.dat` is tracked by git and present in a clean checkout, and the demo's `AOM_science__trans` device reads it during ordinary test collection.

**"If the suite errors rather than skipping cleanly when an optional extra is absent, fix that first" — done, 2026-09-01.** See F.


---

### A real experiment is frozen in the suite **[added 2026-09-22]**

`test/wignertime/fixtures/lab2/` holds a timeline written by **Dániel Varga** for the Lab2 atom-cavity apparatus, taken out of the running experiment on 2026-09-21. 13 KB — description, connections, devices — for a run driving ten analogue and fourteen digital channels over 12.5 s, expanding to 885 601 rows at 2 µs. `test_lab2_regression.py` runs it end to end and checksums the result.

It is worth more than the demo for this purpose, because it was **not written to suit the package**. It carries an apparatus table predating the `to_V` port; a variable (`dispenser__A`) the current naming default refuses, so the test rebinds `config.VARIABLE__REGEX` — the only exercise that mechanism gets anywhere; an analogue channel connected but uncalibrated, which is A14's first real-apparatus case; and ramps whose interpolation was a *closure*, which no durable format can store.

**The checksums pin today's output, not the rig's.** Two deliberate changes account for every difference from what the machine was given, both measured: `drop_repeats`, new on this branch, removes 82.7% of the analogue rows (disabling it reproduces the archived count exactly); and B9 moved the sample grid, so digits differ by at most 20 parts in 65 536 and only on the five channels it touched. Digital output is identical value for value. See the fixture's own `README.md`.

The suite cost is about 4 s, run once per module through scoped fixtures.

**The description was also rebuilt from Lab2's own source, and reproduces exactly** (2026-09-22). Running their stage code and their parameters against the present package gives all 131 rows bit-identical — variables, contexts, times, values — and the same 60 rows carrying a ramp function with the same three sharpnesses. So the origin work of 2026-09-18 (per-slot completion, the terminal chains, the unified bound, A4, A6, A8, B2) changed nothing about what an existing experiment produces. Lab2 uses no string origins, its only two `origin=0.0` are on an `update` and an `anchor` rather than a ramp, and its only 2-D inputs are on `update`, so none of the changed paths is reached.

The whole incompatibility across 488 lines of lab code was: the package rename; `connection.connection` becoming `adwin.connection.new`, which is the one genuine API change; and rebinding `config.VARIABLE__REGEX` for `dispenser__A`. `tl.stack`, `tl.update`, `tl.ramp`, `tl.anchor` and `tl.create` all still take what they took.

The reconstruction lives beside the takeout, not here: it is operation-layer code, and 600 lines of one lab's physics in `test/` would rot against the API exactly as the manuscript's demo listing did (D7). The repository keeps the data; the takeout keeps the derivation.

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