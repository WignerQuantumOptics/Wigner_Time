# Wigner Time — known issues

Standing checklist for code work, written for an agent picking up the repository cold. It holds what is open and the rules in force. The full accounts of the resolved items – reproductions, measurements, and the reasoning behind each decision – are in [`docs/design-record.md`](docs/design-record.md), indexed at the end of this file. Item IDs are stable, and are cited from `CLAUDE.md`, from code comments and docstrings, and from each other, so they are never renumbered.

**Priority order.** Silent failures rank above visible ones. A wrong answer that raises is a nuisance; a wrong answer that returns quietly can sit in an experiment for months.

**Do not "fix" by adding try/except or defensive branching.** This library's value proposition is that experiment descriptions are inspectable data. Failures should be loud and early, at the point where the user's intent was ambiguous – not absorbed downstream.

**Origins have their own reference.** `docs/origin-resolution.md` maps every branch of the origin mechanism as implemented, in four layers. Read it before touching `internal/origin.py`.

## No git state in the records

This file and `docs/design-record.md` hold diagnosis, reasoning and decisions – **never git state**: no branch names or branch state, no commit hashes, no merge state. Refer to work by issue or pull-request number (#85, #161), which survives a squash merge, and to decisions by their dates. Refer to the paper by section label (`sec:adwin`, `tab:rampExamples`, `fig:origin`) or by a quoted phrase, never by line number, since line numbers move with every edit. Where the state of something is wanted, the issue holds it.

## How work is tracked

Every item here has a GitHub issue, and the two carry different things. **This file holds the diagnosis, the measurement and the reasoning; the issue holds the state.**

The scheme below was agreed by both maintainers on 2026-10-02. **Each question is answered in exactly one place**, and every open issue has a type and a milestone; labels are set where they apply.

| question | answered by | rule |
| --- | --- | --- |
| what kind of work? | issue **type** | every open issue has one |
| when, and does it break anything? | **milestone** | every open issue has one; pull requests carry none |
| what can go wrong, and where? | **labels** | the fixed set below |
| which topic? | **parent issue** | topics are parent issues, never milestones or labels |
| who? | **assignee** | only whoever is working on it now |

**Process.** Development happens on one branch per issue, made from `main` and named after its issue (`issue#<n>`), which is opened as a draft pull request once it is pushed, so that it is visible and CI runs on it. Pull requests are **squash-merged** into `main` (maintainer, 2026-10-04), and an issue is closed when its pull request is merged. Closing as work lands is also what makes a parent issue's sub-issue count show progress.

**Milestones.** The paper describes version **1.0.0** (maintainer, 2026-10-01), which freezes the API it prints; after it, what matters about an issue is whether it breaks that API. The descriptions on GitHub are authoritative and reproduced here.

| milestone | what belongs in it |
| --- | --- |
| `1.0 — paper` | Must land before the SciPost paper is published: silent-failure defects, anything that falsifies `docs/paper/main.tex`, the decisions those depend on, and the release itself (#169). |
| `1.x` | After the paper, and compatible with 1.0.0: nothing the paper prints changes, and no code written against 1.0.0 breaks. |
| `2.0` | After the paper, and breaking: changes what the paper prints, or the 1.0.0 API. |
| `ideas` | Worth considering, not committed to. Moves to a numbered milestone once someone takes it on. |

`10 — paper` was renamed to `1.0 — paper`; `20 — internal API` (a topic, now #163 and #167) and `30 — reach & polish` were retired on 2026-10-02.

**Types** are org-level GitHub issue types, not labels – which is why a search for a "decision label" finds nothing: `Bug` (an unexpected problem or behavior), `Task` (a specific piece of work), `Feature` (a request, idea, or new functionality) and `Decision` (an open API or design decision that must be settled before dependent work can proceed). `Decision` carries "flag and ask, never settle unilaterally" onto GitHub; set it on anything whose entry here offers two options rather than a fix. For the ones open now, filter by the type on GitHub.

**Labels**, thirteen:

- **risk, at most one:** `silent` (a wrong answer with no error – outranks visible failures, and puts the item in `1.0 — paper` by default) or `potentially surprising` (not wrong as such, but likely to surprise a user). They exclude each other;
- **`paper-affecting`:** any change falsifies a claim in `main.tex`, so §G applies and the *code* changes;
- **area:** `api` (what users call), `origin`, `adwin`, `dataframe`, `display`, `docs`, `performance`, `hardware` (backends other than ADwin);
- **for contributors:** `good first issue`, `help wanted`.

Retired on 2026-10-02: `ux` and `consistency` (too broad to filter on), `internal refactor` (a `Task` without `api` says it), `future` (now the `ideas` milestone), `extension` (renamed `hardware`), and `duplicate`, `invalid`, `wontfix` (GitHub's close reasons carry them). Deleting a label removed it from closed issues too.

**Topics** are parent issues: **#163** the public API (#166, #168, #138, #69), **#167** the dataframe library (#162), **#169** the 1.0.0 release (#10). #9, the old umbrella of both, was closed as superseded.

**The section letters here are not the labels.** A is silent failures, B correctness, C open decisions, D structural – but a D item can be `silent` (D11, D14, D15, D18 all are), so set the label from the behaviour rather than from the letter.

## Open items

Three items with an ID are open, all in section D and in `1.x`: **D16** (#130), **D23** (#144) and **D24** (#173). Three open issues carry no ID and are recorded at the end of this section.

### D16 — the anchor label cannot be printed on a legacy Windows code page **[new, found 2026-09-11]**

`config.LABEL__ANCHOR` is `⚓` (U+2693). Printing a timeline containing an anchor from a console whose encoding is a legacy Windows code page — cp1250 on the Hungarian-locale machines this package is developed and used on — raises:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2693' in position 706
```

This is not obscure: the recommended convention is that *every user-defined stage ends with an anchor*, so essentially every real timeline contains one, and `print(timeline)` is the most obvious thing a user does with it. Jupyter and any UTF-8 console are unaffected, which is why it has gone unnoticed — but it means the package's own advice produces objects that cannot be inspected from a plain terminal without setting `PYTHONIOENCODING`.

Loud rather than silent, so low severity by this document's ordering. Fixing it properly probably means making the label configurable rather than changing it, since it is also a display affordance.

### D23 — a default that names a config global is bound at import, so rebinding it does nothing **[new, found 2026-09-22]**

**Not D3, despite looking identical.** D3 is a *mutation* hazard: a mutable default can be corrupted by an in-place write, and the fix was to stop `ensure_pair` handing back its caller's object — no signature changed. This is a *configuration* hazard: the object is never mutated, and the failure is that the supported way of changing it silently does not work. Twelve signatures, an API policy decision, and a different label. Folding the two together would have made D3's record dishonest, since the defect it names is fixed and verified.

| global | defaulted in |
| --- | --- |
| `adwin.internal.SPECIFICATIONS__DEFAULT` | `adwin.core.convert`, `adwin.core.upload` (then `create`), `adwin.internal.add`, `add_cycle`, `to_tuples` |
| `conversion.SPECIFICATIONS__DEFAULT` | `conversion.add`, `_add_linear`, `_add_function` |
| `adwin.CONTEXTS__SPECIAL` | `adwin.internal.add_cycle`, `adwin.validate.special_contexts` |
| `adwin.SCHEMA`, `adwin.display.SYMBOL_QUANTITY` | `adwin.validate.types`, `display.quantities` |

Each is bound at import, so **rebinding the global would silently fail to reach any of them**, while mutating it in place would reach all of them. That is the asymmetry removed from `origin.auto` under D3 (`docs/design-record.md`). It is currently latent rather than a broken promise: only `config.VARIABLE__REGEX` is documented as rebindable, and it is genuinely read on every call. But `machine_specifications` is exactly the thing a user has to change for their own rig (D21), and the supported route — passing it explicitly — is the one `upload`, then `create`, ignored until D15 was fixed.

**Not settled here.** Making these `None`-defaulted and read at call time is a consistent policy and touches twelve signatures, so it is an API decision rather than a fix. The natural place is the single ADwin pass that D21 describes, where five of the twelve are being opened anyway.

**Interacts directly with [#142](https://github.com/WignerQuantumOptics/Wigner_Time/issues/142), which pulls the other way.** That issue asks for `origin=ORIGIN_DEFAULT` in place of `origin=None`, so that a signature shows when a default is effective. Read literally it would introduce *this* defect on the three most-used signatures in the package, and would break what the Lab2 fixture relies on — that rebinding a `config` attribute takes effect.

**Both are satisfied by one design**: the signature names an immutable **sentinel**, not the config value, and the body reads the config at call time.

```python
ORIGIN__DEFAULT = Sentinel("ORIGIN__DEFAULT")

def ramp(..., origin=ORIGIN__DEFAULT):
    if origin is ORIGIN__DEFAULT:
        origin = wt_config.ORIGIN__DEFAULTS__RAMP    # read now, not at import
```

**This is the shape #142 took (2026-09-28)**: `wt_config.INFER`, an immutable object that the signatures of `update`, `anchor` and `ramp` name, and that `origin.auto` reads as `None` at call time, so the chains are still looked up on every call. See A8's amendment, in `docs/design-record.md`.

The signature then announces that a default is effective, rebinding still works, nothing mutable is captured at import, and `None` stays free to mean what it means per slot. Measured while checking #142's second claim, that the default cannot easily be turned off — it can, but the spelling differs by function, which nothing at the call site says:

```
ramp(origin=0.0)        -> [0.0, "variable"]   # time absolute, value still from the variable
ramp(origin=[0.0, 0.0]) -> [0.0, 0.0]          # fully off
update(origin=0.0)      -> [0.0, None]         # fully off, update having no value default
```

**Recommendation, not a decision.** `None`-default and read the global inside the body, as `variable.py` already does for `config.VARIABLE__REGEX` and as `origin.auto` now does by requiring the argument outright. That is twelve signatures, five of which the D21 pass opens anyway, so the cost is mostly in the other seven.

**Counter-argument worth stating**, because it is not obviously wrong: these globals are not advertised as rebindable, and the supported route for `machine_specifications` is the parameter. On that reading the right fix is D15 — make the parameter actually work — and leaving the defaults alone is harmless. What makes it worth doing anyway is that the two knobs then behave the same way as `VARIABLE__REGEX`, which *is* advertised, and a user who finds one of them working by rebinding has no way to know the others do not.

Tracked as [#144](https://github.com/WignerQuantumOptics/Wigner_Time/issues/144).

**Applied to the first row only, 2026-09-23 (#94)**, as part of the #94 roadmap the maintainer approved (step 2). `SPECIFICATIONS__DEFAULT` is now read at call time, through `adwin.internal.specifications`, by `core.convert`, `core.upload` (then `create`), `internal.add` and `internal.to_tuples`. `add_cycle` no longer takes the specification at all, since the only thing it read from it was the period. `add_cycle`'s `CONTEXTS__SPECIAL` default was opened by the same change and follows the same rule. The other seven signatures, and the policy question itself, are untouched and remain #144's to decide.

### D24 — `display.quantities` draws a zoomed timeline wrongly outside an interactive window, and draws ramps as jumps **[new, found 2026-10-05]**

Found while regenerating `fig:timeline__example` from `timeline_demo`, which the paper describes as the output of `display.quantities(timeline_demo)`, zoomed. The figure was a screenshot of an interactive window, and stays one (maintainer, 2026-10-06) until this is fixed. Three faults in `adwin/display.py`, measured on `timeline_demo` with `range__x=(15.099, 15.1085)`:

1. **`range__x` is applied before the variable labels exist.** They are created at x = 0, and `_sync_axes`, the `xlim_changed` callback that moves them to the left edge of the view, is connected after `set_xlim` has run. So they stay 15 s outside the window until the view changes once. Interactively the first zoom fires the callback, which is why nobody saw it.
2. **The stage labels of `_draw_context` are not clipped to the axes.** Out of the window they are invisible but still count towards the figure's extent: `fig.get_tightbbox()` is 12 066 in × 7.6 in, from `MOT`'s label at 7.55 s, and `savefig(bbox_inches="tight")` at 200 dpi did not finish in two minutes. Fixing 1 does not fix 2; both were worked around (a second `set_xlim`, `set_clip_on(True)` on every text) to confirm that nothing else was in the way.
3. **A ramp is drawn as a jump at its end.** Rows are joined with `step(where="post")`, and an unexpanded timeline holds a ramp's two boundary rows only, so the start value is drawn held to the ramp's end and jumping there: the molasses coil ramp (−0.98 A → 0 from 15.1 s, 0.9 ms) appears as a step at 15.1009 s. The timeline is right and the picture is wrong, so `potentially surprising` rather than `silent`. One direction, not settled: expand for drawing only, leaving the timeline passed in unchanged.

Cosmetic, for the same pass: the labels of variables sharing a unit overprint each other, a zoomed time axis shows an offset (`+1.51e1`) rather than absolute times, and the stage names are too pale to read.

Tracked as [#173](https://github.com/WignerQuantumOptics/Wigner_Time/issues/173).

### Open without an item ID

- **#142** (`Decision`, `paper-affecting`, `1.0 — paper`) – reopened 2026-09-30, the most urgent open decision: whether `None` keeps, in 1.0.0, its meaning in `origin` and `context`, the same as `INFER`. A meaning of its own would change what every stage that forwards `origin=None` or `context=None` does – the lab's, though no longer the paper's or the demo's (2026-10-06, maintainer): `trigger_camera` in `sec:stacking` takes `origin` with no default, since a *placed* stage names its origin, and `pull_coils` in `sec:demonstration` takes no `context`, since it inherits that of `magnetic_trapping`, which states it once. History: A8's amendment and the paper items, in the design record; D23 is the same question from the configuration side.
- **#160** (`1.0 — paper`) – `finish` should derive the final state from the initial state in the timeline rather than restate it through keywords (maintainer, 2026-09-02). It must keep the intended asymmetry (`MOT_ON` is `False` at `init`, `True` at `finish`: copy, then apply named overrides). **It carries the open remainder of B11**: a stopped run plays the final state only for the channels it names, and the lab's `ADwin_Finish` names neither the MOT coils, nor the dispenser, nor `AOM_science__V` (lab L9), so a run stopped in the magnetic trap leaves the coils at the trap's current, silently. Two directions, neither taken: name them in the lab's `finish()`, or have `upload` refuse or warn when the final state leaves a connected channel unnamed – a change to what `upload` accepts, so the maintainer's to decide. `sec:context`'s claim that every channel is then defined waits on it.
- **#174** (`Decision`, `1.x`) – `config.ORIGIN__DEFAULTS` is a chain tried in order and can be rebound, but an entry that always resolves makes every later one unreachable: `LAST` resolves whenever `ANCHOR` would, so placed before it, it leaves `ANCHOR` dead without any error. The chain is only meaningful with entries that can be absent, such as a context name. Two directions, neither taken: refuse a chain with an always-resolving entry before the last, or stop presenting the chain as configuration. `ORIGIN__DEFAULTS__RAMP` has the same shape. Not paper-affecting: the paper does not mention that the order can be configured (maintainer, 2026-10-06).

## C. API decisions – the rules in force

C1–C7 are all settled (index below). An open API or design decision is flagged and asked, never settled unilaterally; D23 is such, and so is #142.

**Keyword forwarding is a feature, not an accident** (maintainer, 2026-09-02). `default_state` is written once, and a keyword no intermediate stage consumes falls through to it and becomes a variable. Of the three layers, only the last stays permissive: `cascade` routes by stage-name prefix, strictly (C1); `stack` forwards a keyword only as a default, and only one some constituent declares (A5, C6); the core functions' `**vtvc_dict` is an open namespace. *Why:* strictness there would destroy the feature, and in the first two it costs the idiom nothing. Full text, with the known limits: design record, "Design intent — keyword forwarding is a feature".

**The open namespace is narrowed to one stage** (maintainer, 2026-09-02). Only `default_state`, and `init` and `finish` that wrap it, take `**kwargs`; every other stage declares its parameters, so `cascade`'s policy is derived from the target's signature (C1). *Why:* with every stage open, a misspelled argument became a variable and no signature check could tell. Its other half is #160. Full text: design record, "Decision — narrow the open namespace to one stage".

## E. Testing constraints

**A green test suite does not clear the ADwin backend.** Changes under `wignertime/adwin/`, and the ADbasic programs under `resources/ADwin/`, can only be checked for internal consistency; correctness must be verified on the rig. Flag any such change explicitly rather than reporting it as done.

The `ADwin` extra is a pure-Python wrapper that installs on a development machine, so `convert` and everything under `adwin.internal` and `adwin.validate` are genuinely exercised. What is not is anything that talks to a device (`link_device`, `upload`'s writes) and the ADbasic programs themselves; entries that rest on a line-for-line emulation of a `.bas` have evidence, not verification. The demo's calibration file is tracked, and the suite skips cleanly when an optional extra is absent (F).

**A real experiment is frozen in the suite.** `test/wignertime/fixtures/lab2/` holds Dániel Varga's Lab2 timeline, taken off the rig on 2026-09-21 and not written to suit the package; `test_lab2_regression.py` runs it end to end and checksums the result. **The checksums pin today's output, not the rig's**: when one moves, the pipeline changed. `drop_repeats` and B9's sample grid account for every difference from what the machine was given. See the fixture's `README.md`, and the design record's §E.

## F. Resolved — do not re-report

- **`drop_repeats`** in `adwin/validate.py` – designed and in place.
- **`drop_duplicates`** already uses `keep="last"`, not `keep="first"`.
- **`conversion.to_digits`** already rounds correctly; a TODO suggesting otherwise was stale.
- **D1, the `origin.py` self-import** – a module importing itself, removed 2026-09-01.
- **`drop_repeats`'s pandas downcasting `FutureWarning`** on every real export – fixed 2026-09-01; the null-like comparison warning left in the suite was answered with the pandas 3 upgrade (#88, 2026-09-30).
- **Nesting one deferred core call inside another** raises at the point of the mistake – fixed 2026-09-01, broadened as C4.
- **E, the suite aborting when an optional extra is absent** – fixed 2026-09-01.

The full accounts are in the design record's §F.

## G. Standing rule: writing friction is a design signal

The paper and the code are developed together. If a behaviour is awkward to describe in prose, the default response is to change the code, not to write defensive prose around it.

Corollary for code work: if a change makes an existing claim in the manuscript inaccurate or hard to state, **stop and report it** rather than proceeding. Do not edit the paper to match the code.

## Index of resolved items

What each was, its issue, and what replaced it. Every full account is in [`docs/design-record.md`](docs/design-record.md), under a heading that starts with its ID (`### A6 — …`). "Rig" marks an ADwin change that awaits the hardware (§E).

**A. Silent failures** ([record](docs/design-record.md#a-silent-failures))

- A1 — `cascade` dropped unmatched keywords – they raise, each with its reason (C1).
- A2 — `cascade` matched stage names as substrings – prefix-anchored, longest first, settled by signature.
- A3 — `ramp` discarded degenerate ramps whole – zero duration raises; a flat ramp is a hold, kept.
- A4 — `origin.auto` could return `None`; an anchorless `ramp` landed at absolute time – terminal default chains.
- A5 — `stack` turned a stray keyword into a phantom variable – a forwarded keyword must be declared by a constituent.
- A6 — an interwoven `ramp` started from zero – per-slot completion; `None` defers, `0.0` is absolute.
- A7 — `LAST`, `ANCHOR` and contexts accepted as value origins – the value slot takes a number, `VARIABLE` or a variable.
- A8 — a value origin added to a stated ramp start (#142) – moot: a ramp starts where its variable is.
- A9 — reserved origin words shadowed real names – superseded: the words are tags (#158).
- A10 — `create` corrupted long positional rows (#58) – one row rule; positional forms later withdrawn (C5).
- A11 — mixed positional and keyword input dropped the keywords (#132) – raises.
- A12 — a negative ramp duration swapped the endpoints – raises.
- A13 — `ramp` discarded a third point – the count is checked against the ramp function.
- A14 — a mistyped device name disabled its limits (#141) – `device.check_correspondence`, both ways.
- A15 — an upload could land under a running sequence (#151) – `upload` waits, also for the `Par_17` owner.
- A16 — an analogue variable on the digital module (#94) – `check_module_kinds` refuses either mismatch.
- A17 — a ramp inside another ramp of its variable (#157) – overlaps raise, compared exactly.
- A18 — an `update` at a ramp's end lost to it on the hardware (#153) – stable `wt_frame.sort`; `expand` keeps order.

**B. Correctness** ([record](docs/design-record.md#b-correctness))

- B1 — `ramp`'s degenerate-row check aligned on index – aligned on `variable`; moot since #142.
- B2 — `find_every_origin` was order-dependent – the bound is computed once.
- B3 — `previous` sorted a slice in place – superseded with `timeline.previous` (D2).
- B4 — `ramp` wrote through a slice – `.copy()`.
- B5 — `expand` mutated the caller's frame – returns a new one.
- B6 — `expand` assumed `num__bounds` rows per group – the point count belongs to the ramp function.
- B7 — a value-only origin raised a raw `TypeError` – one bound, from the resolved time.
- B8 — `LAST` on an empty timeline raised an opaque error – guarded.
- B9 — a ramp's sampling depended on its position in time – the interval count is rounded first.
- B10 — `stack` could not forward into a nested stage (#136) – one closure threads the keywords.
- B11 — an interrupted run did not restore the default state (#148) – final-state arrays played by `finish:`; rig; remainder in #160.

**C. API decisions** ([record](docs/design-record.md#c-api-decisions))

- C1 — strict `cascade`? – yes, derived from the target's signature.
- C2 — origin parameters on `create`? (#45) – no; `create` is gone (C7).
- C3 — `anchor` with no time – the time is required.
- C4 — the `timeline` argument's contract – `util.ensure_timeline`; nesting rejected.
- C5 — the `*vtvc` / `**vtvc_dict` grammar – variables are keywords; positional forms internal.
- C6 — `stack`'s `context` skipped a leading table (#145) – stages only; a forwarded keyword is a default.
- C7 — composition takes stages only (#85) – `to_timeline(stage, onto=None)`; P0–P6 and N1–N4 done.

**D. Structural** ([record](docs/design-record.md#d-structural))

- D1 — `origin.py` imported itself – removed.
- D2 — `timeline.previous` duplicated `origin.previous` (#116) – deleted.
- D3 — mutable default in `ramp` (#117) – `ensure_pair` never returns its argument.
- D4 — variadics annotated as lists – `*fs: Callable`, in code and paper.
- D5 — `context_info`'s pandas coupling – closed: pandas is the interface.
- D6 — `national_instruments/__init__.py` did not parse – fixed.
- D7 — what `__` separates (#121) – `<device>__<UID>(__<unit>)`; `__` before a unit in user names.
- D8 — `"variable"` resolved on one call path only – `find` says where it is handled.
- D9 — `fig:origin` disagreed with the config (#123) – redrawn, generated by a script.
- D10 — `ensure_pair` typo; `find` normalised twice – fixed.
- D11 — every analogue module converted as ±10 V / 16 bits (#125) – each with its own range, width and gain.
- D12 — digital modules found by `bits == True` (#126) – `bits == 1`; no width raises.
- D13 — `cycle_period__normal__us` held seconds (#127) – `cycle_period`, later an argument (D15).
- D14 — `Initial_Processdelay` unchecked (#128) – `Par_9`/`Par_14`, `PeriodRefused`; rig.
- D15 — `adwin.core.create` ignored two arguments (#129) – `upload` reads the period off the machine.
- D17 — an uncalled `stack` constituent bound the timeline (#131) – tagged stages; tables refused (C7).
- D18 — every digital row went to module 1 (#133) – each to its own module; every digital module programmed.
- D19 — cycle sentinels shared the time axis (#146) – `validate.cycles`; sentinel relieved by B11.
- D20 — ascending cycle order unenforced (#147) – `validate.ascending`.
- D21 — the cycle period stated twice, read from neither (#94) – read off the machine; rig.
- D22 — the console was a second apparatus description (#94) – `wignertime.adwin.console`; rig.

**Paper items tracked by no issue** – all done or settled but #142 (above); listed at the end of the design record.
