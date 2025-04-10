"""
EXPERIMENTAL!!!

TODO:
This is the left-over of an attempt to 'simplify' a previous method for creating realistic timelines. It should be harvested for good ideas and then deleted.



An example implementation of a real Wigner Time timeline.
As well as providing conveniences, the functions can be used to document the intention and meaning of each stage.


"""

# TODO: Change shutter convention! 1 should mean closed and 0 should mean open: this comes from 1->True;0->False and also from the visual symbolism of 0.

import importlib
import pathlib as pl

import pandas as pd
import numpy as np
from munch import Munch
from wigner_time import constructor as construct
from wigner_time import connection as con
from wigner_time import timeline as tl
from wigner_time import adwin as adwin
from wigner_time import util as u

from copy import deepcopy


importlib.reload(tl)
importlib.reload(construct)
# ^^^ Reloads are for development purposes only

###########################################################################
#                       Constants and Helpers                             #
###########################################################################

# TODO: These ↓ (connections, devices and constants) should maybe be read from a separate file (they won't change much).
connections = con.connection(
    ["shutter_MOT", 1, 11],
    ["shutter_repump", 1, 12],
    ["shutter_imaging", 1, 13],
    ["shutter_OP001", 1, 14],
    ["shutter_OP002", 1, 15],
    ["AOM_MOT", 1, 1],
    ["AOM_repump", 1, 2],
    ["AOM_imaging", 1, 5],
    ["AOM_OP_aux", 1, 30],  # should be set to 0 always
    ["AOM_OP", 1, 31],
    ["coil_compensationX__A", 4, 7],
    ["coil_compensationY__A", 3, 2],
    ["coil_MOTlower__A", 4, 1],
    ["coil_MOTupper__A", 4, 3],
    ["coil_MOTlowerPlus__A", 4, 2],
    ["coil_MOTupperPlus__A", 4, 4],
    ["lockbox_MOT__V", 3, 8],
)

# TODO: This could be a set of conversion functions/lambdas from units like A, MHz
devices = pd.DataFrame(
    columns=["variable", "unit_range", "safety_range"],
    data=[
        ["coil_compensationX__A", (-3, 3), (-3, 3)],
        ["coil_compensationY__A", (-3, 3), (-3, 3)],
        ["coil_MOTlower__A", (-5, 5), (-5, 5)],
        ["coil_MOTupper__A", (-5, 5), (-5, 5)],
        ["coil_MOTlowerPlus__A", (-5, 5), (-5, 5)],
        ["coil_MOTupperPlus__A", (-5, 5), (-5, 5)],
        ["lockbox_MOT__V", (-10, 10)],
    ],
)

# TODO:
# I dislike global variables but, unfortunately, a reference will probably still need to be available in the same namespace as these functions for convenience.
constants = Munch(
    safety_factor=1.1,
    factor__VpMHz=0.05,
    Bfield_compensation_Z__A=-0.1,
    Bfield_compensation_Y__A=1.5,
    Bfield_compensation_X__A=0.25,
    lag_MOTshutter=2.48e-3,
    OP=Munch(
        lag_AOM_on=15e-6,
        lag_shutter_on=1.5e-3,
        lag_shutter_off=1.5e-3,
        duration_shutter_on=140e-6,
        duration_shutter_off=600e-6,
    ),
)


# TODO: Move device conversions out of here?
# Idea would be to make ...__A, __MHz etc. variables at the 'top' level of timeline conversion and then we could run the conversion functions later.
class lock_box:
    def to_V(MHz):
        return constants.factor__VpMHz * MHz


# TODO: Should all of the context-creating function arguments be abstracted here?
defaults = Munch()

# NOTE: MOTplus coils are part of the compensation and so should default to the compensation values.
defaults.MOT = Munch(
    lockbox_MOT__V=0.0,
    shutter_MOT=1,  # TODO: why the shutter values here?
    shutter_repump=1,
    coil_MOTlower__A=-1.0,
    coil_MOTupper__A=-0.98,
)

defaults.molasses = Munch(
    duration_cooling=5e-3,
    duration_ramp=1e-3,
    shift__MHz=-80,
    fraction_ramp_duration=0.9,
    coil_MOTlower__A=0.0,
    coil_MOTupper__A=0.0,
)

defaults.magnetic = Munch(
    delay=1e-3,
    quadrupole=Munch(duration_ramp=50e-6, coil_MOTlower__A=-1.8, coil_MOTupper__A=-1.7),
    strong=Munch(duration_ramp=3e-3, coil_MOTlower__A=-4.8, coil_MOTupper__A=-4.7),
)

defaults.finish = Munch(update={}, ramp={})
defaults.finish.update = Munch(
    AOM_MOT=1,
    AOM_repump=1,
    AOM_repump__V=5,
    AOM_imaging=1,
    AOM_OP_aux=0,
    AOM_OP=1,
    AOM_science=1,
    AOM_science__V=0.0,
    AOM_ref=1,
    shutter_MOT=1,
    shutter_repump=1,
    shutter_imaging=0,
    shutter_OP001=0,
    shutter_OP002=1,
    shutter_science=1,
    shutter_transversePump=0,
    shutter_coupling=0,
    trigger_TC__V=0,
    photodiode__V=0,
)
defaults.finish.ramp = Munch(
    coil_MOTlower__A=0.0,
    coil_MOTupper__A=0.0,
    coil_MOTlowerPlus__A=-constants.Bfield_compensation_Z__A,
    coil_MOTupperPlus__A=constants.Bfield_compensation_Z__A,
    coil_compensationX__A=constants.Bfield_compensation_X__A,
    coil_compensationY__A=constants.Bfield_compensation_Y__A,
    lockbox_MOT__V=lock_box.to_V(0.0),
)


###########################################################################
#                   Experimental stages                                   #
###########################################################################
# NOTE: The idea behind the function wrapping is that we enclose what will likely never change and expose just those attributes that we are likely to want to vary.


def init():
    """
    Creates an experimental timeline for the initialization of every relevant variable.
    """
    return tl.create(
        lockbox_MOT__V=0.0,
        coil_compensationX__A=constants.Bfield_compensation_X__A,
        coil_compensationY__A=constants.Bfield_compensation_Y__A,
        coil_MOTlowerPlus__A=-constants.Bfield_compensation_Z__A,
        coil_MOTupperPlus__A=constants.Bfield_compensation_Z__A,
        AOM_MOT=1,
        AOM_repump=1,
        AOM_OP_aux=0,
        AOM_OP=1,
        shutter_MOT=0,
        shutter_repump=0,
        shutter_OP001=0,
        shutter_OP002=1,
        context="ADwin_LowInit",
    )


# TODO: in the true ADwin finish section, nothing time dependent can be done! Another context, called “finish”, which could have special handling also
def finish(
    timeline,
    duration_ramp=1e-3,
    time_start=None,
    vars_set=None,
    vars_ramp=None,
    defaults_set=defaults.finish.set,
    defaults_ramp=defaults.finish.ramp,
    #    context="ADwin_Finish",
):
    """
    Safely winds down the system. Doing this within the ADwin_Finish environment, means that this will still happen when the process is interrupted.

    Here, a previous timeline is not optional.
    """

    _vars_set = construct.arguments(vars_set, defaults_set)
    _vars_ramp = construct.arguments(vars_ramp, defaults_ramp)

    return tl.stack(
        tl.next(**_vars_ramp, t=duration_ramp, timeline=timeline, context="Finish"),
        tl.update(**_vars_set, context="ADwin_Finish"),
    )


# TODO: Should all of these functions simply take a timeline and params?
def MOT(
    detuning__MHz=3,
    duration=10.0,
    # ===
    time_start=None,
    variables: Munch | None = None,
    variables_default=defaults.MOT,
    timeline=init(),
    context="MOT",
):
    """
    Creates a Magneto-Optical Trap.

    """
    _time_start, _variables = construct.time_and_arguments(
        time_start, variables, variables_default, timeline
    )

    return tl.stack(
        tl.create(
            shutter_MOT=_variables.shutter_MOT,
            shutter_repump=_variables.shutter_repump,
            coil_MOTlower__A=_variables.coil_MOTlower__A,
            coil_MOTupper__A=_variables.coil_MOTupper__A,
            # ===
            timeline=timeline,
            context=context,
        ),
        tl.next(
            lockbox_MOT__V=lock_box.to_V(detuning__MHz), t=duration, context="MOT_grow"
        ),
    )


def molasses(
    duration_cooling=5e-3,
    duration_ramp=1e-3,
    detuning__MHz=-80,
    # ===
    # Specific values above ↑
    # Repeated values below ↓
    # ===
    time_start=None,
    variables: Munch | None = None,
    variables_default=defaults.molasses,
    timeline=MOT(),
    context="molasses",
):
    _time_start, _variables = construct.time_and_arguments(
        time_start, variables, variables_default, timeline
    )

    if duration_ramp >= duration_cooling:
        raise ValueError("duration_ramp should be smaller than duration_cooling!")

    return tl.stack(
        tl.create(
            AOM_MOT=[_time_start + duration_cooling, 0],
            shutter_MOT=[_time_start + duration_cooling - constants.lag_MOTshutter, 0],
            timeline=timeline,
            context=context,
        ),
        tl.next(
            coil_MOTlower__A=_variables.coil_MOTlower__A,
            coil_MOTupper__A=_variables.coil_MOTupper__A,
            t=duration_ramp,
        ),
        tl.next(lockbox_MOT__V=lock_box.to_V(detuning__MHz), t=duration_ramp),
    )


def switch_laser(
    var__AOM,
    var__shutter,
    state="ON",
    params=Munch(
        lag_AOM_on=15e-6,
        lag_shutter_on=1.5e-3,
        duration_shutter_on=140e-6,
        safety_factor=1.1,
    ),
    time_start=None,
    timeline=None,
    context=None,
):
    """
    Combines the action of turning off the AOM and turning on the shutter or vice versa, such that a laser beam is changed `ON` or `OFF` according to the given state ENUM.

    """
    # TODO: I live in hope that the shutter convention will be changed!
    #
    _time__AOM = time_start - params.lag_AOM_on - params.lag_shutter_on
    _time__shutter = (
        time_start
        - params.lag_AOM_on
        - params.safety_factor * (params.lag_shutter_on + params.duration_shutter_on)
    )
    _value__AOM = 0 if state == "ON" else 1
    _value__shutter = 1 if state == "ON" else 0

    return tl.update(
        context=context,
        timeline=timeline,
        **{
            var__AOM: [_time__AOM, _value__AOM],
            var__shutter: [
                _time__shutter,
                _value__shutter,
            ],
        },
    )


def flash_laser():
    """
    Switches the laser on and off, for a given duration.
    """
    # TODO: fill in the blank!
    return


def optical_pumping(
    duration_exposure=80e-6,
    duration_ramp=500e-6,
    B_field_homogenous__A=-0.12,
    # ===
    # Specific values above ^
    # Repeated values below ↓
    # ===
    time_start=None,
    variables: Munch | None = None,
    variables_default={},
    timeline=molasses(),
    context="optical_pumping",
):
    """
    Creates an experimental timeline for optical pumping.

    NOTE:
    The AOM is switched off close to, but before, the opening of the first shutter, but taking care not to flash too soon.
    """
    # TODO:
    # - Mysterious constants should be investigated and named!
    # ===
    constant__mysterious_001 = 9.5e-6
    constant__mysterious_002 = 0.5e-6

    _time_start, _variables = construct.time_and_arguments(
        time_start, variables, variables_default, timeline
    )

    return tl.stack(
        switch_laser(
            "AOM_OP",
            "shutter_OP001",
            "OFF",
            time_start=_time_start,
            timeline=timeline,
            context=context,
        ),
        tl.update(
            AOM_OP=[
                _time_start - constants.OP.lag_AOM_on + constant__mysterious_001,
                1,
            ],
            shutter_OP002=[
                _time_start
                + duration_exposure
                - (2 - constants.safety_factor) * constants.OP.lag_shutter_off,
                0,
            ],
        ),
        # Shutters switched back, to reinitialize them before any additional optical pumpings later.
        tl.update(
            AOM_OP=[_time_start + duration_exposure + constant__mysterious_002, 0],
            AOM_repump=[_time_start + duration_exposure, 0],
            shutter_repump=[_time_start + duration_exposure, 0],
            shutter_OP001=[_time_start + duration_exposure, 0],
            shutter_OP002=[
                _time_start
                + duration_exposure
                + constants.safety_factor
                * (constants.OP.lag_shutter_on + constants.OP.duration_shutter_on),
                1,
            ],
        ),
        tl.next(
            coil_MOTlower__A=B_field_homogenous__A,
            coil_MOTupper__A=-B_field_homogenous__A,
            time_start=_time_start - duration_ramp,
            t=duration_ramp,
            context=context,
        ),
    )


optical_pumping()


def ramp_magnetic_coils(
    timeline=None,
    # ===
    time_start=None,
    params: Munch = Munch(
        duration_ramp=150e-3,
        coil_MOTlower__A=0.0,
        coil_MOTupper__A=0.0,
        coil_MOTlowerPlus__A=-constants.Bfield_compensation_Z__A,
        coil_MOTupperPlus__A=constants.Bfield_compensation_Z__A,
    ),
    context=None,
):
    """
    By default, lowers the coil values to safe 'starting' values.
    """
    _time_start = construct.time(time_start, timeline)
    _variables = u.filter_dict(
        params,
        [
            "coil_MOTlower__A",
            "coil_MOTupper__A",
            "coil_MOTlowerPlus__A",
            "coil_MOTupperPlus__A",
        ],
    )

    return tl.next(
        **_variables,
        time_start=_time_start,
        t=params.duration_ramp,
        timeline=timeline,
        context=context,
    )


def make_and_strengthen_magnetic_trap(
    timeline=optical_pumping(), params=defaults.magnetic, context="magnetic_trap"
):
    return tl.stack(
        ramp_magnetic_coils(
            timeline=timeline,
            params=params.quadrupole,
            context=context,
        ),
        lambda t: ramp_magnetic_coils(
            timeline=t,
            params=params.strong,
            context=context,
        ),
    )


def prepare_atoms():
    """
    Convenience for setting up the cold atoms.

    NOTE: `tl.stack` can be used with any single-argument function, where the single argument is a (DataFrame-like) timeline.
    """
    # TODO: should really take the whole parameters dict as an input and use it intelligently.
    return tl.stack(make_and_strengthen_magnetic_trap, finish)


###########################################################################
#                                 SCRATCH                                 #
###########################################################################
duration_cooling = 1e-3
timeline = init()
context = "test"


# data = prepare_atoms()
# print(data)


init = init()

from wigner_time import variable as var


print("here")
mask_current = init["variable"].str.contains("A" + "$")
init
