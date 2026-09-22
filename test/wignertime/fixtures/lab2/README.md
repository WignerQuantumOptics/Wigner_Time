# Lab2 — a real experiment, frozen from the rig

**Experiment written by Dániel Varga**, for the Lab2 atom-cavity apparatus.
**Taken out of the running experiment on 2026-09-21; status as reconciled here: 2026-09-22.**

Used by `../../test_lab2_regression.py`.

| file | rows | what it is |
| --- | --- | --- |
| `timeline.parquet` | 131 | the description: 35 variables, 11 of them anchors, ramps at three sharpnesses |
| `connections.parquet` | 30 | variable → module, channel |
| `devices.parquet` | 13 | conversion and safety range, both in the current schema and as Lab2 states it |

13 KB in total, for a run that drives ten analogue and fourteen digital channels over
12.5 s and expands to 885 601 rows at 2 µs.

## Why this is here and not the demo

`demo/full_experiment.py` exercises the package against an experiment written to suit it.
This one was not. It carries things the demo does not have and would not have been written
to have:

- an apparatus table predating the port to `to_V` / `value__min` / `value__max`;
- a variable, `dispenser__A`, that the current default naming convention refuses, so the
  test rebinds `config.VARIABLE__REGEX` — the mechanism's only exercise anywhere;
- an analogue channel, `imaging_beam_intensity__V`, connected but not calibrated, which
  `device.check_correspondence` refuses. Latent, since that channel carries no rows in
  this run — but it is the first real-apparatus case that check has met;
- ramps whose interpolation was a closure rather than a named function.

## The ramp functions

The takeout stored these in the `function` column as **closures** —
`pull_coils.<locals>.<lambda>` and `atom_cavity.<locals>.<lambda>` — which only `dill`
serialises, and only against a matching Python. No durable format keeps them: the best a
name-based format can write is `'__main__.atom_cavity.<locals>.<lambda>'`, which resolves
to nothing.

Each turned out to be `tanh` with one number baked in, as a free variable or a bytecode
constant, so each is written down instead, in two columns:

| `function` | `function__sharpness` | recovered from |
| --- | --- | --- |
| `wignertime.ramp_function.tanh` | 3.0 | called directly; 3 is the signature default |
| `wignertime.ramp_function.tanh` | 3.0 | `pull_coils` closure, free variable `pt` |
| `wignertime.ramp_function.tanh` | 0.3 | `atom_cavity` closure, bytecode constant |
| `wignertime.ramp_function.tanh` | 1.6 | `atom_cavity` closure, bytecode constant |

Each reconstruction was checked by **calling both** and comparing the curves, not by
reading the bytecode and hoping. `test_every_ramp_function_is_data_rather_than_code`
keeps that true.

This is the one place where a timeline stops being data and becomes code, and it is worth
knowing before designing anything that has to archive one.

## The checksums are today's output, not the rig's

The test pins what the package produces now. The archived tuples the machine was actually
given differ, and every difference is accounted for:

- **`drop_repeats`** is new on this branch and removes **82.7%** of the analogue rows —
  885 542 becomes 153 463. Disabling it reproduces the archived count exactly, row for
  row.
- **`range__inclusive`** (B9, #134) changed the point count of a ramp whose duration is an
  exact multiple of the step. Every tuple still matches on `(cycle, module, channel)`;
  the digits differ by at most 20 parts in 65 536, and only on the five channels B9
  touched.

Digital output is identical, value for value.

So: when a checksum here changes, it means the pipeline changed. Whether that is a
regression or an improvement is for the reader — but it will not pass unnoticed, which is
the whole point of freezing a run.

## Provenance

The originals are three `dill` pickles, 73.5 MB, at
`labSoftware/Lab2TimelineTakeout_VargaDani_20260921/`. Its `converted/` directory has
them in readable formats, the full reconciliation, and the scripts that produced both.
Only the 13 KB here is needed to regenerate the rest, which is why only this is in the
repository.

Note that the takeout was produced against a **pre-rename Wigner Time** (`wigner_time`)
and the `lab2version` branch of the lab code. Lab2 has not yet moved to the current
package.
