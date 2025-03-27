from wigner_time import timeline as tl
from wigner_time.adwin import display as adwin_display

import sys
import pathlib as pl

sys.path.append(str(pl.Path.cwd() / "doc"))
import experimentDemo as ex


def test_displayIndividualTypes():
    tl__new = tl.stack(
        ex.init(shutter_imaging=0, AOM_imaging=1, trigger_camera=0),
        ex.MOT(),
        ex.MOT_detunedGrowth(),
    ).drop(columns="function")

    adwin_display.quantities(tl__new, variables=["shutter_MOT"], do_show=False)
    adwin_display.quantities(tl__new, variables=["lockbox_MOT__MHz"], do_show=False)
    adwin_display.quantities(
        tl__new, variables=["lockbox_MOT__MHz", "shutter_MOT"], do_show=False
    )
