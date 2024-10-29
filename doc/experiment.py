# coding: utf-8
import sys
sys.path.append("..")

import pandas as pd
import numpy as np
from munch import Munch
from wigner_time import connection as con
from wigner_time import timeline as tl
from wigner_time import adwin as adwin
from wigner_time import display as dp


connections = con.connection(
    ["shutter_MOT", 1, 11],
    ["shutter_repump", 1, 12],
    ["shutter_OP001", 1, 14],
    ["shutter_OP002", 1, 15],
    ["AOM_MOT", 1, 1],
    ["AOM_repump", 1, 2],
    ["AOM_OP_aux", 1, 30],  # should be set to 0 always
    ["AOM_OP", 1, 31],
    ["coil_compensationX__A", 4, 7],
    ["coil_compensationY__A", 3, 2],
    ["coil_MOTlower__A", 4, 1],
    ["coil_MOTupper__A", 4, 3],
    ["coil_MOTlowerPlus__A", 4, 2],
    ["coil_MOTupperPlus__A", 4, 4],
    ["lockbox_MOT__MHz", 3, 8],
)

devices = pd.DataFrame(
    columns=["variable", "unit_range", "safety_range"],
    data=[
        ["coil_compensationX__A", (-3, 3), (-3, 3)],
        ["coil_compensationY__A", (-3, 3), (-3, 3)],
        ["coil_MOTlower__A", (-5, 5), (-5, 5)],
        ["coil_MOTupper__A", (-5, 5), (-5, 5)],
        ["coil_MOTlowerPlus__A", (-5, 5), (-5, 5)],
        ["coil_MOTupperPlus__A", (-5, 5), (-5, 5)],
        #["lockbox_MOT__V", (-10, 10)],
        ["lockbox_MOT__MHz", (-200, 200)],
    ],
)


constants = Munch(
    safety_factor=1.1,
#    factor__VpMHz=0.05,
    lag_MOTshutter=2.48e-3,
    Compensation=Munch(
        Z__A=-0.1,
        Y__A=1.5,
        X__A=0.25,
    ),
    OP=Munch(
        lag_AOM_on=15e-6,
        lag_shutter_on=1.5e-3,
        lag_shutter_off=1.5e-3,
        duration_shutter_on=140e-6,
        duration_shutter_off=600e-6,
    ),
    AI=Munch(
        lag_shutter_on=2.2e-3,
        lag_shutter_off=1.9e-3,
    )
)


def init(**kwargs) :
    """
    Creates an experimental timeline for the initialization of every device.
    """
    return tl.stack(
        tl.create(
            lockbox_MOT__MHz=0.0,
            coil_compensationX__A= constants.Compensation.X__A,
            coil_compensationY__A= constants.Compensation.Y__A,
            coil_MOTlowerPlus__A = -constants.Compensation.Z__A,
            coil_MOTupperPlus__A =  constants.Compensation.Z__A,
            AOM_MOT = 1,
            AOM_repump = 1,
            AOM_OP_aux = 0, # TODO: USB-controlled AOMs should be treated on a higher level
            AOM_OP = 1,
            shutter_MOT = 0,
            shutter_repump = 0,
            shutter_OP001 = 0,
            shutter_OP002 = 1,
            context="ADwin_LowInit",
            **kwargs
        ),
        tl.anchor(t=0.0,relativeTime=False,context="InitialAnchor")
    )


def finish(wait=1, lA=-1., uA=-0.98, MOT_ON=True, **kwargs) :
    duration=1e-2
    return tl.stack(
        tl.anchor(wait,context="finalRamps"),
        tl.ramp(
            lockbox_MOT__MHz=0.0,
            coil_MOTlower__A = lA,
            coil_MOTupper__A = uA,
            coil_compensationX__A= constants.Compensation.X__A,
            coil_compensationY__A= constants.Compensation.Y__A,
            coil_MOTlowerPlus__A = -constants.Compensation.Z__A,
            coil_MOTupperPlus__A =  constants.Compensation.Z__A,
            duration=duration,
            context="finalRamps"
        ),
        tl.set(
            AOM_MOT = 1,
            AOM_repump = 1,
            AOM_OP_aux = 0, # TODO: USB-controlled AOMs should be treated on a higher level
            AOM_OP = 1,
            shutter_MOT = int(MOT_ON),
            shutter_repump = int(MOT_ON),
            shutter_OP001 = 0,
            shutter_OP002 = 1,
            t=0.1,
            context="ADwin_Finish",
            **kwargs
        )
    )


def MOT(duration=15, lA=-1., uA=-0.98, **kwargs) :
    return tl.stack(
        tl.set(
#           waitChannel = 0,
            shutter_MOT=1,
            shutter_repump=1,
            coil_MOTlower__A=lA,
            coil_MOTupper__A=uA,
            context='MOT',
            **kwargs
        ),
        tl.anchor(duration)
    )


def MOT_detunedGrowth(duration=100e-3, durationRamp=10e-3, toMHz=-5, pt=3, **kwargs) :
    return tl.stack(
        tl.ramp(
            lockbox_MOT__MHz=toMHz,
            duration=durationRamp,
            fargs={"ti": pt},
            context='MOT',
            **kwargs
        ),
        tl.anchor(duration)
    )


def molasses(duration=5e-3, durationCoilRamp=9e-4, durationLockboxRamp=1e-3, toMHz=-90, coil_pt=3, lockbox_pt=3, **kwargs) :

    return tl.stack(
        tl.ramp(
            coil_MOTlower__A=0,
            coil_MOTupper__A=0, # TODO: can these be other than 0 (e.g. for more perfect compensaton?)
            duration=durationCoilRamp,
            fargs={"ti": coil_pt},
            context="molasses",
            **kwargs
        ),
        tl.ramp(
            lockbox_MOT__MHz=toMHz,
            duration=durationLockboxRamp,
            fargs={"ti": lockbox_pt},
        ),
        tl.set(
            shutter_MOT=[duration - constants.lag_MOTshutter,0],
            AOM_MOT=[duration,0]
        ),
        tl.anchor(duration,context="molasses")
        
    )


def OP(durationExposition=80e-6, durationCoilRamp=50e-6, i=-0.12, pt=3, **kwargs) :
    fullDuration=durationExposition+durationCoilRamp
    return tl.stack(
        tl.ramp(

            coil_MOTlower__A= i,
            coil_MOTupper__A=-i,
            duration=durationCoilRamp,
            fargs={"ti": pt},
            context="OP",**kwargs
        ),
        tl.set("AOM_OP",[[-0.1,0],[durationCoilRamp,1],[fullDuration,0]]),
        tl.set("shutter_OP001",[[durationCoilRamp-constants.OP.lag_shutter_on,1],[0.1,0]]),
        tl.set("shutter_OP002",[[fullDuration-constants.OP.lag_shutter_off,0],[0.1,1]]),
        tl.set(AOM_repump=0,shutter_repump=0,t=fullDuration),
        tl.anchor(fullDuration,context="OP")
        )


def pull_coils(duration, l, u, lp=-constants.Compensation.Z__A, up=constants.Compensation.Z__A, pt = 3, **kwargs) :
    return tl.ramp(
        coil_MOTlower__A=l,
        coil_MOTupper__A=u,
        coil_MOTlowerPlus__A=lp,
        coil_MOTupperPlus__A=up,
        fargs={"ti": pt},
        duration=duration,
        **kwargs,
    )


def magneticTrapping(durationInitial=50e-6, li=-1.8, ui=-1.7, durationStrengthen=3e-3, ls=-4.8, us=-4.7, **kwargs) :
    return tl.stack(
        pull_coils(durationInitial,li,ui,context="magneticTrapping",**kwargs),
        pull_coils(durationStrengthen,ls,us,t=durationInitial),
        tl.anchor(durationInitial+durationStrengthen,context="magneticTrapping")
    )
