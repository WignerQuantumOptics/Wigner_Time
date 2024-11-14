import sys
sys.path.append("..")

import pandas as pd

from munch import Munch
from wigner_time import connection as con
from wigner_time import timeline as tl

import experiment as ex

# Note: make context explicit everywhere, otherwise there is a danger of squashing everything into the Finish context
# due to previous_context when appending to an already `finish`ed timeline

connections=pd.concat([ex.connections,con.connection(["shutter_imaging", 1, 13],["AOM_imaging", 1, 5],["trigger_camera", 1, 0])])

def trigger_camera(t, exposure, context, **kwargs) :
    return tl.set("trigger_camera",[[t,1],[t+exposure,0]],relativeTime=False,context=context,**kwargs)

def flash_light(t, exposure, context, **kwargs) :
    sf = ex.constants.safety_factor
    return tl.stack(
        tl.set("AOM_imaging",[[t,1],[t+exposure,0]],relativeTime=False,context=context,**kwargs),
        tl.set("shutter_imaging",[[t-exposure*(sf-1)-ex.constants.AI.lag_shutter_on,1],[t+exposure*sf,0]],relativeTime=False,context=context),
        # TODO: what to write here exactly?
    )

def expose_camera(t, exposure, context, **kwargs) :
    sf = ex.constants.safety_factor
    return tl.stack(
        flash_light(t, exposure, context, **kwargs),
        trigger_camera(t-exposure*(sf-1)/2, exposure*sf, context)
    )

def take_image_plus_Bg(t, exposure, delayBg, context, **kwargs) :
    return tl.stack(
        expose_camera(t, exposure, context, **kwargs), # taking At image
        trigger_camera(t+delayBg, exposure*ex.constants.safety_factor, context), # taking Bg_At image
    )

def imaging_absorption(t, exposure, delayBg, delayLi, timeline, exposureBlow=None, anchorToContext=None, **kwargs) :
    """
    if anchorToContext is None, time is treated as absolute
    """
    t=tl.time_from_anchor_to_context(timeline,t,anchorToContext)
    context = "imaging_absorption"
    return tl.stack(
        timeline,
        tl.set(AOM_imaging=0,t=t-0.1,relativeTime=False,context=context,**kwargs), # initializing the AOM
        take_image_plus_Bg(t, exposure, delayBg, context), # taking At + Bg_At image
        flash_light(t+delayBg+delayLi/2.,exposureBlow,context) if exposureBlow is not None else None, # blow out the atoms in between
        take_image_plus_Bg(t+delayLi, exposure, delayBg, context), # taking Li + Bg_Li image
        tl.anchor(t+delayLi+2*delayBg,relativeTime=False,context=context)
    )
