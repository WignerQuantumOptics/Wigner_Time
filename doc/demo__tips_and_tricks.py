"""
Here we highlight some convenient features that might not be obvious otherwise.
"""

from wigner.time import timeline as tl

tl.create(AOM_MOT=1, shutter_MOT=1, t=10, context="MOT")

tl.create(AOM_MOT=[0.1, 1], shutter_MOT=[0.0, 1], thing=40, context="MOT")

tl.create(AOM_MOT=[[0.1, 1], [0.2, 0]], context="MOT")
tl.create("AOM_MOT", 0.1, 1, "MOT")

tl.create([["AOM_MOT", 1, 0.1, "MOT"], ["AOM_imaging", 1, 0.0, "AI"]])
