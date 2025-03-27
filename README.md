![Test Status](https://github.com/WignerQuantumOptics/Wigner_Time/actions/workflows/tests.yml/badge.svg)

# Wigner_Time
Timeline creation and management for open-loop control in AMO experiments and beyond.

## Status
This is currently an alpha release. Usable, but subject to breaking changes.
We will release the first stable version soon.


## Optional dependencies (package `extras`) 
 - `performance_and_export` (Recommended): Installs `pyarrow` for memory management, sharing between systems and export to `parquet`.
 - `display`: Installs `matplotlib` and `pyqt` for visualization.
 - `parallel_processing`: Installs `polars` for parallel dataframe manipulation. (WARNING: This is currently not used, but will be in the future)
