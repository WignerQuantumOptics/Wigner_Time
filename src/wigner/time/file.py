"""
For PC-level loading and saving of stored timelines. 
"""

import pathlib as pl


def save(timeline, path=None, file_type="parquet"):
    """
    Writes the given timeline to file.
    """
    # TODO:
    # - WIP
    # - tests
    if path is None:
        path = pl.Path.cwd()
    return


def load(path):
    """
    Reads the given file into memory.
    """
    return
