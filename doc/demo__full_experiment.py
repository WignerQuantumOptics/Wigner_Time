"""
An example implementation of a real experiment, using 'Wigner Time' timelines.

As well as providing conveniences, the functions can be used to document the intention and meaning of each stage.
"""

# TODO: WIP!!!
# TODO: buzz words: extensibility. flexibility and composability
# TODO: We should use readable variable names (in general too, but this is a demo)
# TODO:
# - Should probably have some imaging in here?
# - Should go all the way to generating a full timeline (adding connections, devices etc.)


from typing import Callable
import pandas as pd

from munch import Munch
from wigner_time.adwin import connection as adcon
from wigner_time import timeline as tl
from wigner_time import device
from wigner_time import conversion as conv
from wigner_time import ramp_function


###########################################################################
#                       Constants and Helpers                             #
###########################################################################

# Connections, devices and constants can be read from a separate file(s) (they won't change much). They are all collected together here for demonstration purposes only.

"""
'connections' allows us to label physical links (inputs and outputs) between devices and the timing system. By using labels that follow a particular regex, defined within the `variable` module, we can separate out the design and the implementation of our experiment.
"""
# TODO: Should all analogue variables be Voltages here?
connections = adcon.new(
    ["shutter_MOT", 1, 11],
    ["shutter_repump", 1, 12],
    ["shutter_OP001", 1, 14],
    ["shutter_OP002", 1, 15],
    ["shutter_science", 1, 10],
    ["shutter_transversePump", 1, 9],
    ["AOM_MOT", 1, 1],
    ["AOM_repump", 1, 2],
    ["AOM_OPaux", 1, 30],  # should be set to 0 always
    ["AOM_OP", 1, 31],
    ["coil_compensationX__A", 4, 7],
    ["coil_compensationY__A", 3, 2],
    ["coil_MOTlower__A", 4, 1],
    ["coil_MOTupper__A", 4, 3],
    ["coil_MOTlowerPlus__A", 4, 2],
    ["coil_MOTupperPlus__A", 4, 4],
    ["lockbox_MOT__MHz", 3, 8],
    ["trigger_TC__V", 3, 1],
    ["AOM_science", 1, 4],
    ["AOM_science__V", 4, 8],
)

"""
'devices' stores how to map our physical quantities to an implementation voltage, as well as specifying the range of values that should be allowed for this variable.
"""
devices = device.new(
    ["coil_compensationX__A", 1 / 3.0, -3, 3],
    ["coil_compensationY__A", 1 / 3.0, -3, 3],
    ["coil_MOTlower__A", 1 / 2.0, -5, 5],
    ["coil_MOTupper__A", 1 / 2.0, -5, 5],
    ["coil_MOTlowerPlus__A", 1 / 2.0, -5, 5],
    ["coil_MOTupperPlus__A", 1 / 2.0, -5, 5],
    ["lockbox_MOT__MHz", 0.05, -200, 200],
    ["trigger_TC__V", 1.0, -10, 10],
    [
        "AOM_science__trans",
        conv.function_from_file(
            "resources/calibration/aom_calibration.dat",
            sep=r"\s+",
        ),
        0.0,
        1.0,
    ],
)


"""
'constants' allow us to store site-specific details that help define our exeriment.
"""
constants = Munch(
    safety_factor=1.1,
    #    factor__VpMHz=0.05,
    lag__MOTshutter=2.3e-3,
    lag__repump_shutter=0,  # Earlier value, yet unverified: 2.3e-3,
    Compensation=Munch(
        Z__A=-0.1,
        Y__A=1.5,
        X__A=0.25,
    ),
    OP=Munch(
        lag__AOM_on=15e-6,
        lag__shutter_on=1.48e-3,
        lag__shutter_off=1.78e-3,
        duration__shutter_on=140e-6,
        duration__shutter_off=600e-6,
    ),
    AI=Munch(
        lag__shutter_on=2.2e-3,
        lag__shutter_off=1.9e-3,
    ),
)


###########################################################################
#                   Experimental stages                                   #
###########################################################################
# NOTE: The idea behind the function wrapping is that we enclose what will rarely change and expose just those attributes that we are likely to want to vary.


def default_state(f=tl.create, MOT_ON=True, **kwargs):
    """
    Starts/leaves the system in a sane state that is appropriate for creating a new timeline

    As a general rule, AOMs are kept on as long as possible to keep them in thermal equilibrium. When needed, we turn them off before the opening of the shutter.
    """
    return tl.stack(
        f(
            lockbox_MOT__MHz=0.0,
            coil_compensationX__A=constants.Compensation.X__A,
            coil_compensationY__A=constants.Compensation.Y__A,
            coil_MOTlowerPlus__A=-constants.Compensation.Z__A,
            coil_MOTupperPlus__A=constants.Compensation.Z__A,
            AOM_MOT=1,
            AOM_repump=1,
            AOM_OPaux=0,  # TODO: USB-controlled AOMs should be treated on a higher level
            AOM_OP=1,
            AOM_science=1,
            shutter_MOT=int(MOT_ON),
            shutter_repump=int(MOT_ON),
            shutter_OP001=0,
            shutter_OP002=1,
            shutter_science=0,
            shutter_transversePump=0,
            AOM_science__V=5.0,
            trigger_TC__V=0.0,
            **kwargs,
        )
    )


def init(f=tl.create, MOT_ON=False, **kwargs):
    return default_state(
        f=f,
        t=-1e-6,  # time is simply a placeholder here as 'ADwin_LowInit' is a 'special' context, that will be treated differently by the ADwin system.
        context="ADwin_LowInit",
        MOT_ON=MOT_ON,
        **kwargs,
    )


def finish(wait=1, lA=-1.0, uA=-0.98, MOT_ON=True, **kwargs):
    """
    Safely winds down the system, 'ramping' the analog variables to the “default state” in a given duration by the default `ramp_function`.

    The `anchor` function is used to specify a key time instant, around which other times can be specified.

    The ADwin_Finish environment means that the “default state” will be actuated even when the process is interrupted.
    """
    duration = 1e-2
    # TODO:
    # - The default_state function should be used to populate the ramp?
    # - check if the second context is needed
    # - check if the anchor is needed
    return tl.stack(
        tl.anchor(wait, context="finalRamps"),
        tl.ramp(
            lockbox_MOT__MHz=0.0,
            coil_MOTlower__A=lA,
            coil_MOTupper__A=uA,
            coil_compensationX__A=constants.Compensation.X__A,
            coil_compensationY__A=constants.Compensation.Y__A,
            coil_MOTlowerPlus__A=-constants.Compensation.Z__A,
            coil_MOTupperPlus__A=constants.Compensation.Z__A,
            duration=duration,
            context="finalRamps",
        ),
        default_state(
            f=tl.update,
            t=duration
            + 1e-6,  # time is just fictive here, the important thing is the context
            context="ADwin_Finish",
            MOT_ON=MOT_ON,
            **kwargs,
        ),
    )


def MOT(duration=15, lA=-1.0, uA=-0.98, **kwargs):
    """
    Creates a Magneto-Optical Trap.
    """
    return tl.stack(
        tl.update(
            shutter_MOT=1,
            shutter_repump=1,
            coil_MOTlower__A=lA,
            coil_MOTupper__A=uA,
            context="MOT",
            origin=0.0,
            **kwargs,
        ),
        tl.anchor(duration, origin=0.0, context="MOT"),
    )


def MOT__detuned_growth(
    duration=100e-3, duration__ramp=10e-3, detuning__MHz=-5, **kwargs
):  # pt=3,
    """
    Final stage of MOT collection with detuned MOT beams for increased capture range.
    """
    return tl.stack(
        tl.ramp(
            lockbox_MOT__MHz=detuning__MHz,
            duration=duration__ramp,
            #            fargs={"ti": pt},
            context="MOT",
            **kwargs,
        ),
        tl.anchor(duration),
    )


def molasses(
    duration=5e-3,
    durationCoilRamp=9e-4,
    durationLockboxRamp=1e-3,
    toMHz=-90,  # coil_pt=3, lockbox_pt=3,
    delay=0,  # arbitrary delay to shutter for ad hoc compensation of small drifts
    **kwargs
):

    return tl.stack(
        tl.ramp(
            coil_MOTlower__A=0,
            coil_MOTupper__A=0,  # TODO: can these be other than 0 (e.g. for more perfect compensaton?)
            duration=durationCoilRamp,
            #            fargs={"ti": coil_pt},
            context="molasses",
            **kwargs,
        ),
        tl.ramp(
            lockbox_MOT__MHz=toMHz,
            duration=durationLockboxRamp,
            #            fargs={"ti": lockbox_pt},
        ),
        tl.update(
            shutter_MOT=[duration - constants.lag__MOTshutter + delay, 0],
            AOM_MOT=[duration, 0],
        ),
        tl.anchor(duration, context="molasses"),
    )


def optical_pumping(
    duration__exposition=80e-6,
    duration__coil_ramp=50e-6,
    i=-0.12,  # pt=3,
    delay1=0,
    delay2=0,
    delay__repump=0,  # arbitrary delays to shutters for ad hoc compensation of small drifts
    **kwargs
):
    """
    Creates an experimental timeline for optical pumping.

    NOTE:
    The AOM is switched off close to, but before, the opening of the first shutter

    TODO:
    Shutters are reinitialized so that additional optical pumping stages can be added later.
    However, this should probably be factorized out.

    """

    duration__full = duration__exposition + duration__coil_ramp
    return tl.stack(
        tl.ramp(
            coil_MOTlower__A=i,
            coil_MOTupper__A=-i,
            duration=duration__coil_ramp,
            #            fargs={"ti": pt},
            context="OP",
            **kwargs,
        ),
        tl.update(AOM_OP=[[-0.1, 0], [duration__coil_ramp, 1], [duration__full, 0]]),
        tl.update(
            shutter_OP001=[
                [duration__coil_ramp - constants.OP.lag__shutter_on + delay1, 1],
                [0.1, 0],
            ]
        ),
        tl.update(
            shutter_OP002=[
                [duration__full - constants.OP.lag__shutter_off + delay2, 0],
                [0.1, 1],
            ]
        ),
        tl.update(
            shutter_repump=0,
            t=duration__full - constants.lag__repump_shutter + delay__repump,
        ),
        tl.update(AOM_repump=0, t=duration__full),
        tl.anchor(duration__full, context="OP"),
    )


def pull_coils(duration, l, u, lp=0, up=0, pt=3, **kwargs):
    return tl.ramp(
        coil_MOTlower__A=l,
        coil_MOTupper__A=u,
        coil_MOTlowerPlus__A=lp - constants.Compensation.Z__A,
        coil_MOTupperPlus__A=up + constants.Compensation.Z__A,
        function=lambda origin, terminus, time_resolution: ramp_function.tanh(
            origin, terminus, time_resolution, pt
        ),
        duration=duration,
        **kwargs,
    )


def magnetic_trapping(
    duration__initial=50e-6,
    li=-1.8,
    ui=-1.7,
    duration__strengthen=3e-3,
    ls=-4.8,
    us=-4.7,
    **kwargs
):
    return tl.stack(
        pull_coils(duration__initial, li, ui, context="magneticTrapping", **kwargs),
        pull_coils(duration__strengthen, ls, us, t=duration__initial),
        tl.anchor(duration__initial + duration__strengthen, context="magneticTrapping"),
    )


def MOT_off(**kwargs):
    return tl.update(shutter_MOT=0, AOM_MOT=0, shutter_repump=0, AOM_repump=0, **kwargs)


[
    # MOT
    Munch(
        duration=15,
        lA=-1.0,
        uA=-0.98,
    ),
    # MOT detuned
    Munch(
        duration=0.1,
        durationRamp=1e-2,
        toMHz=-5,  # pt=3,
    ),
    # molasses
    Munch(
        duration=4.5e-3,
        durationCoilRamp=9e-4,
        durationLockboxRamp=1e-3,
        toMHz=-90,
        delay=-200e-6,
    ),
    # optical pumping
    Munch(
        durationExposition=80e-6,
        durationCoilRamp=500e-6,
        i=-0.12,
        delay1=-350e-6,
        delay2=450e-6,
        delayRepump=0,
        wait=1e-3,
    ),
    Munch(
        durationInitial=50e-6,
        li=-1.8,
        ui=-1.7,
        durationStrengthen=3e-3,
        ls=-4.8,
        us=-4.7,
    ),
]


def prepare_atoms(
    stage="finish",
    # Basic setup
    init: Callable = init,
    init_MOT_ON=True,
    finish: Callable = finish,
    finish_MOT_ON=True,
    # MOT stage
    MOT_duration=15,
    MOT_lA=-1.0,
    MOT_uA=-0.98,
    # MOT detuned stage
    MOT_Delta_duration=0.1,
    MOT_Delta_durationRamp=1e-2,
    MOT_Delta_toMHz=-5,  # pt=3,
    # molasses stage
    molasses_duration=4.5e-3,
    molasses_durationCoilRamp=9e-4,
    molasses_durationLockboxRamp=1e-3,
    molasses_toMHz=-90,
    molasses_delay=-200e-6,
    # OP stage
    OP_durationExposition=80e-6,
    OP_durationCoilRamp=500e-6,
    OP_i=-0.12,
    OP_delay1=-350e-6,
    OP_delay2=450e-6,
    OP_delayRepump=0,
    OP_wait=1e-3,
    # magnetic trapping stage
    MT_durationInitial=50e-6,
    MT_li=-1.8,
    MT_ui=-1.7,
    MT_durationStrengthen=3e-3,
    MT_ls=-4.8,
    MT_us=-4.7,
):
    def pipeline():
        yield "init", init(MOT_ON=init_MOT_ON)
        yield "MOT", MOT(MOT_duration, MOT_lA, MOT_uA)
        yield "MOT_delta", MOT__detuned_growth(
            MOT_Delta_duration,
            MOT_Delta_durationRamp,
            MOT_Delta_toMHz,
        )
        yield "molasses", molasses(
            molasses_duration,
            molasses_durationCoilRamp,
            molasses_durationLockboxRamp,
            molasses_toMHz,
            molasses_delay,
        )
        yield "optical_pump", optical_pumping(
            OP_durationExposition,
            OP_durationCoilRamp,
            OP_i,
            OP_delay1,
            OP_delay2,
            OP_delayRepump,
        )
        yield "magnetic_trap", tl.stack(
            tl.anchor(OP_wait, context="OP_wait"),
            magnetic_trapping(
                MT_durationInitial, MT_li, MT_ui, MT_durationStrengthen, MT_ls, MT_us
            ),
        )
        yield "finish", finish(MOT_ON=finish_MOT_ON)

    def run_pipeline(stage=None):
        tline = None
        for s, f in pipeline():
            if callable(f):
                tline = f(tline)
            else:
                tline = f
            if s == stage:
                if s in ["MOT", "MOT_delta"]:
                    return MOT_off(timeline=tline)
                else:
                    return tline
        return tline

    return run_pipeline(stage)


print(prepare_atoms()[["variable", "value", "context"]])

# TODO: (new idea)
# Specify function and variable and the helper function will pass it on nicely?

def blah(*fs, **kws):
    names = [f.__name__ for f in fs]
    f_k = [list(k.split("___"))+[kws[k]], for k in kws.keys()]

    # Check that the given functions and arguments match
    if f is not in names:
        raise ValueError("Some keywords did not match a given function.")

    # Match the given functions and kws

    return 5
