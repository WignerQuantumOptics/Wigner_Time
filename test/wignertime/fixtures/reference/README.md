# References for the #85 migration

**Frozen on 2026-09-29 from `793287a` on `issue#85`**, the code as it stood before P1 of the
roadmap (C7 in `KNOWN_ISSUES.md`, and the roadmap comment on #85). Used by
`../../test_reference.py`; the cases themselves are defined in `../../reference_cases.py`.

| file | what it is |
| --- | --- |
| `demo.parquet` | `timeline__demo` (99 rows), and the same with the camera trigger of `sec:interweaving` placed at molasses |
| `quantum_optics_lab.parquet` | the lab's `prepare_sample` at all five stages × finish on/off × dispenser switch-off on/off; absorption imaging interwoven into each stage; three time-of-flight delays placed onto one base (28 cases) |
| `arrays.json` | row counts and digests of the ADwin arrays of `timeline__demo` and of one whole lab shot (`imaging at MT`), at 5, 2 and 1 µs |

Each case is stored as its base columns plus, for ramp rows, the ramp function's name and
its curve on a fixed input (`reference_cases.FUNCTION__SAMPLE`). The name is only for the
reader. The curve is what is compared, so a renamed function is not a change and an altered
one is. Rows are compared in order, to 1e-12 in each column: among rows sharing an instant,
the one written last is in effect.

The lab cases need the lab's package next door, `../quantum_optics_lab`, on the path:

    PYTHONPATH=.. poetry run pytest test/wignertime/test_reference.py

Without it they are skipped. Between P2 and P5 they are expected to fail, because the
package's API will have moved while the lab's code has not; once the lab is migrated (P5),
they are its acceptance test.

Regenerate only when a change of output is intended, and say so in the commit:

    PYTHONPATH=.. poetry run python test/wignertime/reference_cases.py
