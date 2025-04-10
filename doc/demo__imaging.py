import sys
import pandas as pd
from munch import Munch

from wigner_time.adwin import connection as con
from wigner_time import timeline as tl

import demo__full_experiment as ex

# Note: make context explicit everywhere, otherwise there is a danger of squashing everything into the Finish context
# due to previous_context when appending to an already `finish`ed timeline

connections = pd.concat(
    [
        ex.connections,
        con.new(
            ["shutter_imaging", 1, 13], ["AOM_imaging", 1, 5], ["trigger_camera", 1, 0]
        ),
    ]
)


# this is an upper estimate of the IDS ueye camera exposition delay
DELAY__CAMERA_EXPOSITION = 100e-6


def camera_exposition(exposition__AOM, delay__camera=DELAY__CAMERA_EXPOSITION):
    return exposition__AOM + 2 * delay__camera


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
def flash_light(t, exposure__AOM, context, origin=None, **kwargs):
    sf = ex.constants.safety_factor
    return tl.stack(
        tl.update(
            "AOM_imaging",
            [[t, 1], [t + exposure__AOM, 0]],
            context=context,
            origin=origin,
            **kwargs
        ),
        tl.update(
            "shutter_imaging",
            [
                [t - exposure__AOM * (sf - 1) - ex.constants.AI.lag__shutter_on, 1],
                [t + exposure__AOM * sf, 0],
            ],
            context=context,
            origin=origin,
        ),
    )


def expose_camera(
    t,
    exposure__AOM,
    context,
    origin=None,
    delay__camera=DELAY__CAMERA_EXPOSITION,
    **kwargs
):
    return tl.stack(
        flash_light(t, exposure__AOM, context, origin, **kwargs),
        trigger_camera(
            t - delay__camera,
            exposure__AOM + 2 * delay__camera,
            context,
            origin,
        ),
    )


def image_plus_background(
    t, exposure__AOM, delay__background, context, origin, **kwargs
):
    return tl.stack(
        expose_camera(t, exposure__AOM, context, origin, **kwargs),  # taking At image
        trigger_camera(
            t + delay__background,
            camera_exposition(exposure__AOM),
            context,
            origin,
        ),  # taking Bg_At image
    )


def absorption_image(
    t,
    exposure__AOM,
    origin,
    delay__background=50e-3,
    delay__beam=0.2,
    advance__AOM_off=0.1,
    exposure__blow=1e-2,
    context="imaging__absorption",
    **kwargs
):
    """
    An atomic absorption image is constructed from an image of the imaging beam, an image of the atoms and associated background images.
    """

    return tl.stack(
        tl.update(
            AOM_imaging=0,
            t=t - advance__AOM_off,
            context=context,
            origin=origin,
            **kwargs
        ),  # initializing the AOM
        image_plus_background(
            t, exposure__AOM, delay__background, context, origin
        ),  # taking At + Bg_At image
        (
            flash_light(
                t + delay__background + delay__beam / 2.0,
                exposure__blow,
                context,
                origin,
            )
            if exposure__blow is not None
            else None
        ),  # blow out the atoms in between
        image_plus_background(
            t + delay__beam, exposure__AOM, delay__background, context, origin
        ),  # taking Li + Bg_Li image
    )
