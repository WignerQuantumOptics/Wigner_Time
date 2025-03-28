import sys

sys.path.append("..")

import pandas as pd

from munch import Munch
from wigner_time import connection as con
from wigner_time import timeline as tl

import demonstration as ex

# Note: make context explicit everywhere, otherwise there is a danger of squashing everything into the Finish context
# due to previous_context when appending to an already `finish`ed timeline

connections = pd.concat(
    [
        ex.connections,
        con.connection(
            ["shutter_imaging", 1, 13], ["AOM_imaging", 1, 5], ["trigger_camera", 1, 0]
        ),
    ]
)


# this is an upper estimate of the possible delay of the exposition of the IDS ueye camera:
camera_exposition_margin = 100e-6


def camera_exposition_from_AOM_exposition(AOM_exposition):
    return AOM_exposition + 2 * camera_exposition_margin


def init(**kwargs):
    return ex.init(shutter_imaging=0, AOM_imaging=1, trigger_camera=0, **kwargs)


def finish(**kwargs):
    return ex.finish(shutter_imaging=0, AOM_imaging=1, trigger_camera=0, **kwargs)


def trigger_camera(
    t,
    exposure,
    context,
    origin=None,
    **kwargs  # this can contain e.g. an already existing timeline
):
    return tl.update(
        "trigger_camera",
        [[t, 1], [t + exposure, 0]],
        context=context,
        origin=origin,
        **kwargs
    )


# From this point onwards, exposure is AOM_exposure (so that camera and shutter exposure must be larger)
def flash_light(t, exposure, context, origin=None, **kwargs):
    sf = ex.constants.safety_factor
    return tl.stack(
        tl.update(
            "AOM_imaging",
            [[t, 1], [t + exposure, 0]],
            context=context,
            origin=origin,
            **kwargs
        ),
        tl.update(
            "shutter_imaging",
            [
                [t - exposure * (sf - 1) - ex.constants.AI.lag_shutter_on, 1],
                [t + exposure * sf, 0],
            ],
            context=context,
            origin=origin,
        ),
        # TODO: what to write here exactly?
    )


def expose_camera(t, exposure, context, origin=None, **kwargs):
    return tl.stack(
        flash_light(t, exposure, context, origin, **kwargs),
        trigger_camera(
            t - camera_exposition_margin,
            exposure + 2 * camera_exposition_margin,
            context,
            origin,
        ),
    )


def take_image_plus_Bg(t, exposure, delayBg, context, origin, **kwargs):
    return tl.stack(
        expose_camera(t, exposure, context, origin, **kwargs),  # taking At image
        trigger_camera(
            t + delayBg,
            camera_exposition_from_AOM_exposition(exposure),
            context,
            origin,
        ),  # taking Bg_At image
    )


def imaging_absorption(
    t,
    exposure,
    origin,
    context="AI",
    delayBg=50e-3,
    delayLi=0.2,
    AOM_offAdvance=0.1,
    exposureBlow=1e-2,
    **kwargs
):
    context = "imaging_absorption"
    return tl.stack(
        tl.update(
            AOM_imaging=0,
            t=t - AOM_offAdvance,
            context=context,
            origin=origin,
            **kwargs
        ),  # initializing the AOM
        take_image_plus_Bg(
            t, exposure, delayBg, context, origin
        ),  # taking At + Bg_At image
        (
            flash_light(t + delayBg + delayLi / 2.0, exposureBlow, context, origin)
            if exposureBlow is not None
            else None
        ),  # blow out the atoms in between
        take_image_plus_Bg(
            t + delayLi, exposure, delayBg, context, origin
        ),  # taking Li + Bg_Li image
        #        tl.anchor(t+delayLi+2*delayBg,context=context,origin=origin)
    )


def prepareSample(initFunction=init, finishFunction=finish, **kwargs):
    return ex.prepare_atoms(
        initFunction=initFunction, finishFunction=finishFunction, **kwargs
    )
