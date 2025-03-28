"""
An example implementation of a real experiment, using 'Wigner Time' timelines.

As well as providing conveniences, the functions can be used to document the intention and meaning of each stage.
"""

# TODO: WIP!!!
# TODO: We should use readable variable names (in general too, but this is a demo)


import pandas as pd

from munch import Munch
from wigner_time.adwin import connection as adcon
from wigner_time import timeline as tl
from wigner_time import device
from wigner_time import conversion as conv
from wigner_time import ramp_function
from enum import IntEnum


###########################################################################
#                       Constants and Helpers                             #
###########################################################################

# TODO: What exactly is a stage, do we need the Enum and should it be in the example file?

# Stages, connections, devices and constants can be read from a separate file(s) (they won't change much). They are all collected together here for demonstration purposes only.
Stage = IntEnum(
    "Stage",
    [
        ("MOT", 1),
        ("MOT_Delta", 2),
        ("molasses", 3),
        ("OP", 4),
        ("MT", 5),
    ],
)

"""
'connections' allows us to label physical links (inputs and outputs) between devices and the timing system. By using labels that follow a particular regex, defined within the `variable` module, we can separate out the design and the implementation of our experiment.
"""
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
'constants' allows us to store site-specific details that help define our exeriment.
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
        duration_shutter_on=140e-6,
        duration_shutter_off=600e-6,
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
    return f(
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


def init(MOT_ON=False, **kwargs):
    return default_state(
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


def MOT_detunedGrowth(duration=100e-3, durationRamp=10e-3, toMHz=-5, **kwargs):  # pt=3,
    """
    Final stage of MOT collection with detuned MOT beams for increased capture range.
    """
    return tl.stack(
        tl.ramp(
            lockbox_MOT__MHz=toMHz,
            duration=durationRamp,
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


def OP(
    durationExposition=80e-6,
    durationCoilRamp=50e-6,
    i=-0.12,  # pt=3,
    delay1=0,
    delay2=0,
    delayRepump=0,  # arbitrary delays to shutters for ad hoc compensation of small drifts
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

    fullDuration = durationExposition + durationCoilRamp
    return tl.stack(
        tl.ramp(
            coil_MOTlower__A=i,
            coil_MOTupper__A=-i,
            duration=durationCoilRamp,
            #            fargs={"ti": pt},
            context="OP",
            **kwargs,
        ),
        tl.update(AOM_OP=[[-0.1, 0], [durationCoilRamp, 1], [fullDuration, 0]]),
        tl.update(
            shutter_OP001=[
                [durationCoilRamp - constants.OP.lag__shutter_on + delay1, 1],
                [0.1, 0],
            ]
        ),
        tl.update(
            shutter_OP002=[
                [fullDuration - constants.OP.lag__shutter_off + delay2, 0],
                [0.1, 1],
            ]
        ),
        tl.update(
            shutter_repump=0,
            t=fullDuration - constants.lag__repump_shutter + delayRepump,
        ),
        tl.update(AOM_repump=0, t=fullDuration),
        tl.anchor(fullDuration, context="OP"),
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


def magneticTrapping(
    durationInitial=50e-6,
    li=-1.8,
    ui=-1.7,
    durationStrengthen=3e-3,
    ls=-4.8,
    us=-4.7,
    **kwargs
):
    return tl.stack(
        pull_coils(durationInitial, li, ui, context="magneticTrapping", **kwargs),
        pull_coils(durationStrengthen, ls, us, t=durationInitial),
        tl.anchor(durationInitial + durationStrengthen, context="magneticTrapping"),
    )


# should probably not have `**kwargs` to avoid confusions
def prepare_atoms(
    stage=Stage.MT,
    # init stage
    initFunction=init,
    init_MOT_ON=True,
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
    # finish stage
    finishFunction=finish,
    finish_MOT_ON=True,
):

    # TODO: upgrade to a 'pipeline'
    # def pipeline():
    #     yield "init", init
    #     yield "MOT", MOT
    #     yield "MOT_delta", None
    #     yield "molasses", None
    #     yield "optical_pump", None
    #     yield "magnetic_trap", None

    # def run_pipeline(stage=None):
    #     tline = None
    #     for s, f in pipeline():
    #         print(stage)
    #         tline = f(timeline=tline)
    #         if s == stage:
    #             return tline
    #     return tline

    # run_pipeline("MOT")

    def _():
        def MOT_off(**kwargs):
            return tl.update(
                shutter_MOT=0, AOM_MOT=0, shutter_repump=0, AOM_repump=0, **kwargs
            )

        timeline = MOT(
            MOT_duration, MOT_lA, MOT_uA, timeline=initFunction(MOT_ON=init_MOT_ON)
        )
        if stage == Stage.MOT:
            return MOT_off(timeline=timeline)

        timeline = MOT_detunedGrowth(
            MOT_Delta_duration,
            MOT_Delta_durationRamp,
            MOT_Delta_toMHz,
            timeline=timeline,
        )
        if stage == Stage.MOT_Delta:
            return MOT_off(timeline=timeline)

        timeline = molasses(
            molasses_duration,
            molasses_durationCoilRamp,
            molasses_durationLockboxRamp,
            molasses_toMHz,
            molasses_delay,
            timeline=timeline,
        )
        if stage == Stage.molasses:
            return timeline  # MOT_off(timeline=timeline) should not be necessary in principle

        timeline = OP(
            OP_durationExposition,
            OP_durationCoilRamp,
            OP_i,
            OP_delay1,
            OP_delay2,
            OP_delayRepump,
            timeline=timeline,
        )
        if stage == Stage.OP:
            return timeline

        return tl.stack(
            timeline,
            tl.anchor(OP_wait, context="OP_wait"),
            magneticTrapping(
                MT_durationInitial, MT_li, MT_ui, MT_durationStrengthen, MT_ls, MT_us
            ),
        )

    return tl.stack(_(), finishFunction(MOT_ON=finish_MOT_ON))
