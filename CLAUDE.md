# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
poetry install --with dev --all-extras   # what CI does
poetry run pytest                        # whole suite, from the repo root
poetry run pytest test/wigner/time/test_drop_repeats.py                              # one file
poetry run pytest test/wigner/time/test_drop_repeats.py::test_channels_are_independent  # one test
poetry run pytest -k ramp                # by name

poetry run black src test                # formatter used throughout
poetry run isort src test
poetry run pyflakes src

poetry run mkdocs serve                  # docs from docs/, API page is generated from docstrings
```

There is no pytest configuration and no `conftest.py`; the suite relies on the project being installed
(`poetry install`) and on being run from the repo root.

`test_file.py` writes through `file.save`, which resolves relative paths against the cwd and
auto-increments rather than overwriting. Running the suite therefore leaves `timeline__demo*.{parquet,csv,json,pickle,feather}`
in the repo root, one new numbered set per run. They are gitignored and safe to delete.

## Working rules

`KNOWN_ISSUES.md` is the standing checklist for code work and is **authoritative over this file** on
anything it covers. Read it before touching `timeline.py` or `internal/origin.py`. Its rules:

- **Do not "fix" by adding try/except or defensive branching.** Failures should be loud and early, at
  the point where the user's intent was ambiguous — not absorbed downstream. The value proposition is
  that experiment descriptions are inspectable data.
- **Silent failures outrank visible ones.** A wrong answer that raises is a nuisance; one that returns
  quietly can sit in an experiment for months.
- **Section C items are open API decisions — flag and ask, never settle unilaterally.** Same for the
  intended behaviour of `ramp`'s degenerate-row filtering (A3): silently dropping a user's ramp may be
  worse than expanding a degenerate one, and that call is the maintainers'.
- **A green suite does not clear the ADwin backend.** Changes under `wignertime/adwin/` can only be
  checked for internal consistency; correctness must be verified on the rig. Say so explicitly rather
  than reporting such a change as done.
- **The paper and the code are developed together.** If a change makes a claim in `docs/paper/main.tex`
  inaccurate or hard to state, stop and report it. Do not edit the paper to match the code. If a
  behaviour is awkward to describe in prose, that is a signal to change the code.

## Primary reference

`docs/paper/main.tex` is the most comprehensive description of the project: a SciPost Physics Codebases
submission (Clark, Sárközi, … Vukics) that states the design rationale, not just the API. Read it
before any non-trivial design decision. Useful section map: `sec:definitions` (the three layers),
`sec:origin` + appendix `sec:origin_full` (the complete `origin` specification and resolution order),
`sec:functions` (`create`/`update`/`ramp`/`anchor` with input-format tables), `sec:context`,
`sec:stacking` and `sec:interweaving`, `sec:adwin` (the whole real-time program, in ~15 lines),
`sec:discussion` (comparison with labscript / ARTIQ / Cicero / Entangleware, and stated future work).

The manuscript is now committed and self-contained under `docs/paper/`, imported from Overleaf:
`main.tex`, `SciPost.cls`, `SciPost_bibstyle.bst`, `WignerTime.bib`, and all five figures under
`docs/paper/graphic/`. Every `\includegraphics` target and the `\bibliography{WignerTime.bib}` call
resolve. No LaTeX toolchain is installed here, so a build has not been demonstrated — and note that
`minted` requires `pygmentize` and `-shell-escape`. Build from inside `docs/paper/`; the figure paths
are relative to it.

The Overleaf import is byte-identical to the copy analysed on 2026-09-01/02 — 1453 lines, and every
citation recorded in `KNOWN_ISSUES.md` still lands on the same line — so paper references in these
notes remain valid as written.

For the `origin` mechanism specifically, read `docs/origin-resolution.md` first: it maps every branch
of the resolution as *implemented*, in four layers, with the defect in each. `sec:origin` and
`sec:origin_full` describe the intended design, which the code does not currently match.

## Architecture

The governing idea, and the one to preserve: **the experimental description is data, not a
program.** Comparable systems (labscript, ARTIQ, Cicero, Entangleware) describe an experiment as a
program that is *executed to emit* hardware instructions, so the description is consumed as it is
produced. Here the description is a table — a value — which is why it can be plotted, filtered,
diffed between runs, archived next to its data, or handed to a collaborator without the hardware.
Hardware enters at exactly one point, the conversion step. Accordingly: no in-place modification and
no global state; every core function returns a new timeline, and user-defined stages should too.

A *timeline* is a `pandas.DataFrame`, nothing more. The base schema is `timeline._SCHEMA`
(`time`, `variable`, `value`, `context`) — hence **vtvc**, the name behind `*vtvc` and `**vtvc_dict`
throughout the input plumbing. Every other column is bolted on by a later stage (`module`/`channel`
from `connection`s, `to_V`/`value__min`/`value__max` from `device`s, `value__digits` from
`conversion`, `cycle` from `adwin`). Users are expected to fall back to plain pandas whenever the
conveniences don't fit.

Three named layers, with movement in both directions as an explicit goal:

- **operation** — experiment stages ("take a fluorescence image"). *Client code, deliberately not
  part of the package*; `demo/full_experiment.py` is an example of it, not an API.
- **device** — the vtvc timeline in real physical units (MHz, A). The core abstraction, `timeline.py`.
- **connection** — hardware-ready arrays ("send 5 V to connection 2"), produced solely by
  `adwin/core.py::convert`. Porting to other hardware means writing a new conversion here plus a
  consumer program on the controller; nothing above this layer should need to change.

`device` and `connection` are two separate tables on purpose: recalibrating a device and rewiring
the apparatus are independent operations, each touching one place. Never fold module/channel numbers
into device conversions or vice versa.

### The dual-return idiom

`create`, `update`, `ramp`, `anchor` and `expand` all return **a timeline when `timeline=` is passed,
and a curried callable when it is not**. The callable branch is produced by
`internal/util.py::function__lambda`, which reads the caller's frame to capture its own arguments — so
it only works when called directly from the public function's body. `stack` and `cascade` compose
those callables (and forward their own kwargs into every one of them). Any new top-level timeline
function should follow this shape.

This is what lets a stage be written once, generically, relative only to its own beginning, and
inserted anywhere later. `create` and `update` are otherwise near-identical; they differ only in how
they compose — `create` is the entry point of a stack, `update` can appear anywhere inside one.
`cascade` adds prefix-routed keyword forwarding (`MOT_duration=...` reaches `MOT`'s `duration`), so a
whole experiment has a single point of contact for its nested parameters.

**Deferred calls compose as siblings of a `stack`, never by nesting.** `expand(ramp(...))` looks like
composition but passes a function in as `expand`'s `timeline`; write
`stack(timeline, ramp(...), expand(...))` instead. All five functions now raise a `TypeError` naming
the mistake (`util.ensure_not_deferred`), so this is self-correcting — but `stack` and `cascade` take a
leading callable *legitimately* and must stay outside that guard.

A related trap the guard cannot catch: **`expand` acts on the whole timeline it receives**, not on the
adjacent ramp. Mid-`stack` in a late stage it expands every ramp accumulated so far, and since it then
drops the `function` column, the `expand` inside `adwin.core.convert` becomes a no-op and the
hand-passed resolution is what reaches the hardware. For per-ramp resolution, bake it into the
`function` argument as `demo.pull_coils` does.

### Origins — why chaining is causal by default

`internal/origin.py` is the heart of the package. An `origin` is a `[time, value]` pair where each
slot may be a number or a string. Reserved strings: `anchor`, `last`, `variable` (a per-variable
self-reference); anything else is resolved as a `variable` name, then as a `context`. `origin.update`
shifts a newly built fragment's `time`/`value` per variable relative to the preceding timeline, which
is what makes `stack(timeline, update(...), ramp(...))` join end-to-end without explicit times.
Defaults live in `config.ORIGIN__DEFAULTS`.

Three properties of the mechanism that are easy to break:

- **The flexibility exists only at construction time and never leaks into the data.** Once resolved,
  a timeline holds nothing but absolute times and values; any origin could equally have been written
  as a numeric coordinate. Don't introduce a column or a marker that defers resolution.
- **Value lookups against a variable are bounded in time** — the value *in effect at the origin
  instant*, not the variable's last value in the timeline overall. This is what the `time__max` /
  `time__max__relative` plumbing in `origin.py` is for, and what makes interweaving see the state that
  physically precedes it.
- **`ramp` is the exception that carries a value-relative default**, and it matters. It bypasses
  `config.ORIGIN__DEFAULTS` for its own `[["anchor", "variable"]]`, because a ramp must look up where
  the variable currently sits; `update` needs no value origin since its values are absolute. The paper
  claims no default is value-relative (`sec:origin_full`) — that claim is wrong, see KNOWN_ISSUES A6.
  The consequence to know before writing an interwoven ramp: `origin` given explicitly *replaces* that
  default instead of completing it, and a bare context name pads to `[name, None]`, so
  `ramp(..., origin="stage1")` silently starts the ramp from **0.0**. Write
  `origin=["stage1", "variable"]`.

*Anchors* are a non-physical variable named `⚓` (`config.LABEL__ANCHOR`), auto-numbered `⚓_001`, used
as a time reference within a `context`. They deliberately have no `connection`, so
`adwin.connection.remove_unconnected_variables` drops them at export. Their purpose is that the
instants that matter physically are often ones where nothing is commanded — a MOT collection ends
because enough time has passed, not because a device switched. **Every user-defined stage is
recommended to end with an anchor** carrying that stage's context; the anchor-then-last default is
what then turns every `t` into a Δt from the end of the preceding stage.

### Context does three jobs

`context` carries no timing information and is never sent to the hardware, but it is not decoration:
it is documentation that survives into the archived data (and drives `timeline.context_info` and the
display grouping); it is addressable as an `origin`, which makes a stage a *named region* and is the
basis of interweaving; and a backend may reserve particular names (`ADwin_LowInit`, `ADwin_Finish`).

Contexts are **inherited, not repeated** — `update`, `ramp` and `anchor` adopt the latest context of
the timeline they extend, and any `context=` given to `stack` is forwarded to all its constituents. The
corresponding trap, flagged in `timeline.update`'s docstring: rows appended after a stage in a reserved
context silently inherit that reserved context, so name the context explicitly when extending past one.

### Variable naming is load-bearing, not cosmetic

`variable.py::REGEX` — `equipment_context__unit`; **no `__unit` suffix means the line is digital**.
`connection.new` rejects names that don't match, `conversion`/`device` key off the unit, and
`adwin/display.py` groups plots by it.

### Ramps are stored as functions, then expanded

`ramp` writes two boundary rows plus a callable in a `function` column. `timeline.expand` applies it
to produce one row per point and drops the `function` column — a one-way operation, done only just
before hardware export. `expand`'s `**function_args` are filtered against each function's signature
by `util.function__filtered_kws`; that is how `time_resolution` reaches `ramp_function.tanh` from
`adwin.core.convert`.

### ADwin export pipeline

`adwin/core.py::convert` composes, in order:

1. `connection.remove_unconnected_variables` — anything without a physical port disappears (anchors).
2. `timeline.expand` — ramps become rows at the machine's cycle period.
3. `adwin/internal.py::add` — join `connections` + `devices`, `conversion.add` → `value__digits`,
   `device.check_within_range` (raises, listing every offending variable), `add_cycle`.
4. `adwin/validate.py::all` — `types` → `special_contexts` → `drop_duplicates` → `drop_repeats`.
5. `internal.to_tuples` — `[[(cycle, module, channel, digits), ...analogue], [...digital]]`.

`adwin/core.py::create` then pushes that into `Par_1..3` and `Data_10..13` / `Data_20..23` of the
machine. The consumer is `resources/ADwin/WignerTimeADwin.bas` (ADbasic, real-time side); its
`#define`s and `data_NN` array meanings must stay in sync with `core.create`.

**Keep the real-time program arithmetic-free.** Its whole job is "at this cycle, if a value differs
from the previous one, output it": one comparison per channel group, early exit, no computation. Every
instruction in the event loop must finish within one cycle, so logic there is paid for directly in
temporal resolution — the ADbasic implementation this replaced evaluated `tanh` in-loop and was
limited to a 5 µs cycle; the present system runs the same experiments at 1 µs. The design is a
deliberate trade of computation for memory, which is the entire reason `expand` exists. Proposals that
move logic back into ADbasic to save rows are going the wrong way.

Two distinct kinds of filtering, easy to confuse: `drop_duplicates` removes *temporal* collisions
(two rows for one variable rounding to the same cycle); `drop_repeats` removes *value* redundancy
(a row commanding a channel to the value it already holds), grouped by physical channel rather than
by variable, and always keeping the first and last row of each channel — `core.create` derives the
run length from the highest non-special cycle, and tanh ramp tails are flat.

`adwin/__init__.py::CONTEXTS__SPECIAL` (`ADwin_LowInit`, `ADwin_Init`, `ADwin_Finish`) map to sentinel
cycle numbers. Rows in these contexts have **no meaningful time**, so they are validated separately
(at most one row per variable) and exempted from both drop functions.

## Conventions

- **`__` separates a name from its qualifier or unit; `_` separates words inside the name.** It runs
  through everything: columns (`value__digits`), kwargs (`duration__initial`, `column__value`,
  `timeline__past`), functions (`mask__changed`, `sanitize__round_value`), and the `variable` regex.
  Trailing `__002` on filenames is `file.py`'s collision suffix. Note the scope limit from D7: this
  governs library-internal identifiers, and `docs/paper/main.tex` overrides it for anything the paper shows.
- **Route dataframe operations through `internal/dataframe.py`** (imported as `wt_frame`), not through
  pandas directly. That module exists so a polars backend can be dropped in later; `wt_frame.CLASS` is
  the dataframe type. Several older modules (`conversion.py`, `device.py`, `adwin/connection.py`,
  `internal/timeline/inherit.py`) still import pandas and carry TODOs about it — don't add more.
- Optional dependencies are gated at import time with `importlib.util.find_spec` and a raised
  `ImportError` (`adwin/core.py` needs `ADwin`, `display.py` needs `matplotlib`). Keep new optional
  code importable-but-inert the same way.
- Standard aliases: `tl` (timeline), `wt_frame`, `wt_origin`, `wt_util`, `wt_config`, `wt_adwin`.
- Numpy-style docstrings (mkdocstrings is configured for them). Prose in docstrings tends to explain
  *why* a rule exists, not just what the function does — match that.
- `internal/` is explicitly unstable API. `internal/doc/` and `doc/` are org-mode notes and scratch
  notebooks, not built documentation; `docs/` is the mkdocs source (`docs/index.md` duplicates the
  README, so changes to the overview belong in both). The paper lives in its own self-contained
  subtree, `docs/paper/`; neither it nor `docs/origin-resolution.md` is in `mkdocs.yml`'s nav.
- Tests live under `test/wigner/time/`, mirroring the *old* package name — the package was renamed to
  `wignertime` and the test tree wasn't. Tests build frames as literal row lists and compare with
  `wt_frame.assert_equal`; behaviour with many input shapes is covered via `@pytest.mark.parametrize`
  over calls to `tl.create` and friends.

## Known rough edges

For bugs and open API decisions, **`KNOWN_ISSUES.md` is the list.** Do not duplicate it here, and do
not re-report its section F. Its items were verified against the live repo on 2026-09-01; D1 (the
`origin.py` self-import) and E (the suite aborting when an optional extra was absent) were fixed then,
and the verification results are recorded in the entries themselves.

One live trap worth knowing before you write any `ramp`, because it is silent: **A4** — a `ramp` onto a
timeline containing no `anchor` lands at absolute time, so it can be placed *before* the rows it was
appended to. `ramp` passes an anchor-only `origin__defaults`, so the `config.ORIGIN__DEFAULTS`
fallback does not save it. Following the "every stage ends with an anchor" convention masks it.

Not covered by `KNOWN_ISSUES.md`:

- `internal/constructor.py` calls `tl.previous_time`, which no longer exists — that module is dead code.
- `internal/timeline/validate.py` is documented as out of date with respect to the current schema
  (it references `unit_range`/`safety_range` columns that `device.py` no longer produces).
- `black` does not currently pass on the repo: `device.py`, `internal/dataframe.py`,
  `internal/doc/diagnosticsDemo.py` and `test_check_within_range.py` want reformatting (the first two
  and the last are from the two most recent commits, so this branch introduced them). Format files you
  touch; a repo-wide `black` run would bury your diff.
- **The paper's demo listing (`sec:demonstration`) is a cleaned-up variant of
  `src/wignertime/demo/full_experiment.py`, not a copy of it**, and the two have drifted: the paper
  uses single-underscore parameter names (`duration_coil_ramp`, `lag_MOT_shutter`,
  `lower_current_initial`, `to__MHz`), the code uses the `__` convention (`duration__coil_ramp`,
  `lag__MOTshutter`, `li`/`ui`, `toMHz`); the paper has `shutter_OP1`/`shutter_OP2` and
  `MOT_detuned_growth` against the code's `shutter_OP001`/`shutter_OP002` and `MOT__detuned_growth`;
  and the paper adds a `MOT_off` stage and a `delay_shutter_reinitialization` parameter that the code
  inlines as `0.1`. The paper also renames the ADbasic subroutine `processSwitches` to
  `processUpdates`. **`docs/paper/main.tex` is canonical: when they disagree, the code changes** (maintainer
  decision, 2026-09-02 — see `KNOWN_ISSUES.md` D7 for the inventory and the prerequisites). This
  governs only what the paper actually shows; internal identifiers it never mentions keep the `__`
  convention below.
- `drop_repeats` (on the current branch) implements what `sec:discussion` still describes as future
  work in a commented-out paragraph — timing analog transitions at the instants the DAC code actually
  changes, per Kowalski *et al.* Its docstring argues the filtering is *equivalent* to bit-flip-timed
  expansion on the hardware's own grid, not an approximation to it. That paragraph is worth reviving
  rather than leaving commented out.
- The other stated gap is peripherals programmed over serial rather than driven by a voltage (DDS
  being the canonical case). The paper commits to implementing this as an `expand`-shaped conversion —
  one device-layer row becoming several bit-level rows — rather than as a special case.
