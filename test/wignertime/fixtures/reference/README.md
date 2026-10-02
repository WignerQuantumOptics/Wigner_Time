# References for the #85 migration

**Frozen on 2026-09-29 from `793287a` on `issue#85`**, the code as it stood before P1 of the
roadmap (C7 in `KNOWN_ISSUES.md`, and the roadmap comment on #85). Used by
`../../test_reference.py`; the cases themselves are defined in `../../reference_cases.py`.

**The two tables were regenerated once, on 2026-09-29, for #154 (P4):** the rows in
`ADwin_LowInit` moved from their fictional −1 µs to −∞, and those in `ADwin_Finish` from 1 µs
after the final ramps to +∞. That was checked case by case before regenerating. Every other
row, and every other column of those rows, is unchanged. `MOT` lost its two `origin=0.0`
(in the demo and in the lab), since the first timed stage is now placed at absolute zero by
default. `arrays.json` did not change: the arrays are identical at 5, 2 and 1 µs.

**And a second time, the same day, for D7 (#121):** variable names moved to
`<device>__<UID>(__<unit>)` (`shutter_MOT` → `shutter__MOT`, `coil_MOTlower__A` →
`coil__MOT_lower__A`, the anchors `⚓_001` → `⚓__001`), and the demo's
`timeline__demo` became `timeline_demo`, its case key here too. Checked before
regenerating: every case of both tables is identical once the old names are mapped to
the new, and the digests in `arrays.json` are unchanged (only its key moved).

**And a third time, on 2026-10-01, for #163:** `ramp_function` moved into `timeline`, so the
stored function names `wignertime.ramp_function.tanh` became
`wignertime.timeline.ramp_function.tanh` (52 rows in `demo.parquet`, 422 in
`quantum_optics_lab.parquet`). Only that column was rewritten, in place; every other column
was checked to be identical, and `arrays.json` did not change.

| file | what it is |
| --- | --- |
| `demo.parquet` | `timeline_demo` (99 rows), and the same with the camera trigger of `sec:interweaving` placed at molasses |
| `quantum_optics_lab.parquet` | the lab's `prepare_sample` at all five stages × finish on/off × dispenser switch-off on/off; absorption imaging interwoven into each stage; three time-of-flight delays placed onto one base (28 cases) |
| `arrays.json` | row counts and digests of the ADwin arrays of `timeline_demo` and of one whole lab shot (`imaging at MT`), at 5, 2 and 1 µs |

Each case is stored as its base columns plus, for ramp rows, the ramp function's name and
its curve on a fixed input (`reference_cases.FUNCTION__SAMPLE`). The name is only for the
reader. The curve is what is compared, so a renamed function is not a change and an altered
one is. Rows are compared in order, to 1e-12 in each column: among rows sharing an instant,
the one written last is in effect.

The lab cases need the lab's package next door, `../quantum_optics_lab`, on the path:

    PYTHONPATH=.. poetry run pytest test/wignertime/test_reference.py

Without it they are skipped. They call the lab through the API of its `issue#85` branch,
where `prepare_sample` and the imaging are stages; that migration (P5, 2026-09-29)
reproduces every case, and these were its acceptance test. Against a lab branch from before
it they fail, because the package's API moved in P2.

Regenerate only when a change of output is intended, and say so in the commit:

    PYTHONPATH=.. poetry run python test/wignertime/reference_cases.py
