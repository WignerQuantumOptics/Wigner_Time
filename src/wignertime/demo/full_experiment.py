# SPDX-FileCopyrightText: 2024 Thomas W. Clark and András Vukics
# SPDX-License-Identifier: GPL-3.0-or-later

"""
An example implementation of a real experiment, using 'Wigner Time' timelines.

As well as providing conveniences, the functions can be used to document the intention and meaning of each stage.
"""

import math

from munch import Munch

from wignertime.adwin import connection as adcon
from wignertime import file as wtfile
from wignertime import timeline as tl
from wignertime import device
from wignertime import conversion as conv
from wignertime import ramp_function

###########################################################################
#                       Constants and Helpers                             #
###########################################################################

# Connections, devices and constants can be read from a separate file(s) (they won't change much). They are all collected together here for demonstration purposes only.

"""
'connections' allows us to label physical links (inputs and outputs) between devices and the timing system. By using labels that follow a particular regex, configurable as `config.VARIABLE__REGEX`, we can separate out the design and the implementation of our experiment.
"""
connections = adcon.new(
    ["shutter__MOT", 1, 11],
    ["shutter__repump", 1, 12],
    ["shutter__OP1", 1, 14],
    ["shutter__OP2", 1, 15],
    ["shutter__science", 1, 10],
    ["shutter__transverse_pump", 1, 9],
    ["AOM__MOT", 1, 1],
    ["AOM__repump", 1, 2],
    ["AOM__OP_aux", 1, 30],  # should be set to 0 always
    ["AOM__OP", 1, 31],
    ["coil__compensation_X__A", 4, 7],
    ["coil__compensation_Y__A", 3, 2],
    ["coil__MOT_lower__A", 4, 1],
    ["coil__MOT_upper__A", 4, 3],
    ["coil__MOT_lower_plus__A", 4, 2],
    ["coil__MOT_upper_plus__A", 4, 4],
    ["lockbox__MOT__MHz", 3, 8],
    ["trigger__TC__V", 3, 1],
    ["AOM__science", 1, 4],
    ["AOM__science__trans", 4, 8],
    ["trigger__camera", 1, 0],
)

"""
`devices` stores how to map our physical quantities to an implementation voltage, as well as specifying the range of values that should be allowed for this variable. A linear conversion is the factor taking the unit *to* volts, so a device whose permitted range spans the controller's full output is `10 / limit` — `10 / 5.0` for a coil driven over +/-5 A by a +/-10 V DAC.

These specifications are deliberately separated from `connection`s because they represent physical properties and conversions that are independent of the particular DAC wiring.
"""
devices = device.new(
    ["coil__compensation_X__A", 10 / 3.0, -3, 3],
    ["coil__compensation_Y__A", 10 / 3.0, -3, 3],
    ["coil__MOT_lower__A", 10 / 5.0, -5, 5],
    ["coil__MOT_upper__A", 10 / 5.0, -5, 5],
    ["coil__MOT_lower_plus__A", 10 / 5.0, -5, 5],
    ["coil__MOT_upper_plus__A", 10 / 5.0, -5, 5],
    ["lockbox__MOT__MHz", 0.05, -200, 200],
    ["trigger__TC__V", 1.0, -10, 10],
    [
        "AOM__science__trans",
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
    lag_MOT_shutter=2.3e-3,
    lag_repump_shutter=0,  # Earlier value, yet unverified: 2.3e-3,
    Compensation=Munch(
        Z__A=-0.1,
        Y__A=1.5,
        X__A=0.25,
    ),
    OP=Munch(
        lag_AOM_on=15e-6,
        lag_shutter_on=1.48e-3,
        lag_shutter_off=1.78e-3,
        duration_shutter_on=140e-6,
        duration_shutter_off=600e-6,
    ),
)


###########################################################################
#                   Experimental stages                                   #
###########################################################################
# NOTE: The idea behind the function wrapping is that we enclose what will rarely change and expose just those attributes that we are likely to want to vary.


def default_state(MOT_ON=True, **kwargs):
    """
    Starts/leaves the system in a sane state that is appropriate for creating a new timeline

    As a general rule, AOMs are kept on as long as possible to keep them in thermal equilibrium. When needed, we turn them off before the opening of the shutter. The same holds for the coils.

    The same stage at both ends of the experiment: `init` and `finish` differ only in the
    time, the context and `MOT_ON`.
    """
    return tl.stack(
        tl.update(
            lockbox__MOT__MHz=0.0,
            coil__compensation_X__A=constants.Compensation.X__A,
            coil__compensation_Y__A=constants.Compensation.Y__A,
            coil__MOT_lower_plus__A=-constants.Compensation.Z__A,
            coil__MOT_upper_plus__A=constants.Compensation.Z__A,
            AOM__MOT=1,
            AOM__repump=1,
            AOM__OP_aux=0,  # TODO: USB-controlled AOMs should be treated on a higher level
            AOM__OP=1,
            AOM__science=1,
            shutter__MOT=MOT_ON,
            shutter__repump=MOT_ON,
            shutter__OP1=0,
            shutter__OP2=1,
            shutter__science=0,
            shutter__transverse_pump=0,
            AOM__science__trans=1.0,
            trigger__TC__V=0.0,
            **kwargs,
        )
    )


def init(MOT_ON=False, **kwargs):
    return default_state(
        time=-math.inf,  # before the run: no instant, and 'ADwin_LowInit' is a 'special' context that the ADwin system plays before its event loop (#154)
        context="ADwin_LowInit",
        MOT_ON=MOT_ON,
        **kwargs,
    )


def finish(wait=1, lower_current=-1.0, upper_current=-0.98, MOT_ON=True, **kwargs):
    """
    Safely winds down the system, 'ramping' the analog variables to the “default state” in a given duration by the default `ramp_function`.

    The `anchor` function is used to specify a key time instant, around which other times can be specified.

    The ADwin_Finish environment means that the “default state” will be actuated even when the process is interrupted.
    """
    duration = 1e-2
    # TODO:
    # - The default_state function should be used to populate the ramp?
    return tl.stack(
        tl.anchor(wait, context="finalRamps"),
        tl.ramp(
            lockbox__MOT__MHz=0.0,
            coil__MOT_lower__A=lower_current,
            coil__MOT_upper__A=upper_current,
            coil__compensation_X__A=constants.Compensation.X__A,
            coil__compensation_Y__A=constants.Compensation.Y__A,
            coil__MOT_lower_plus__A=-constants.Compensation.Z__A,
            coil__MOT_upper_plus__A=constants.Compensation.Z__A,
            duration=duration,
            context="finalRamps",
        ),
        default_state(
            time=math.inf,  # after the run: no instant, and 'ADwin_Finish' is played when it ends, or is stopped (#154)
            context="ADwin_Finish",
            MOT_ON=MOT_ON,
            **kwargs,
        ),
    )


def MOT(duration=15, lower_current=-1.0, upper_current=-0.98):
    """
    Creates a Magneto-Optical Trap.
    """
    return tl.stack(
        tl.update(
            shutter__MOT=1,
            shutter__repump=1,
            coil__MOT_lower__A=lower_current,
            coil__MOT_upper__A=upper_current,
        ),
        tl.anchor(duration),
        context="MOT",
    )


def MOT_off():
    return tl.update(shutter__MOT=0, AOM__MOT=0, shutter__repump=0, AOM__repump=0)


def MOT_detuned_growth(duration=100e-3, duration_ramp=10e-3, detuning__MHz=-5):  # pt=3,
    """
    Final stage of MOT collection with detuned MOT beams for increased capture range.
    """
    return tl.stack(
        tl.ramp(
            lockbox__MOT__MHz=detuning__MHz,
            duration=duration_ramp,
            #            fargs={"ti": pt},
        ),
        tl.anchor(duration),
        context="MOT",
    )


def molasses(
    duration=5e-3,
    duration_coil_ramp=9e-4,
    duration_lockbox_ramp=1e-3,
    to__MHz=-90,  # coil_pt=3, lockbox_pt=3,
    delay=0,  # arbitrary delay to shutter for ad hoc compensation of small drifts
):
    """
    For slowing down the atoms by creating an optical density.
    """

    return tl.stack(
        tl.ramp(
            coil__MOT_lower__A=0,
            coil__MOT_upper__A=0,
            duration=duration_coil_ramp,
            #            fargs={"ti": coil_pt},
        ),
        tl.ramp(
            lockbox__MOT__MHz=to__MHz,
            duration=duration_lockbox_ramp,
            #            fargs={"ti": lockbox_pt},
        ),
        tl.update(
            shutter__MOT=[duration - constants.lag_MOT_shutter + delay, 0],
            AOM__MOT=[duration, 0],
        ),
        tl.anchor(duration),
        context="molasses",
    )


def optical_pumping(
    duration_exposition=80e-6,
    duration_coil_ramp=50e-6,
    i=-0.12,  # pt=3,
    delay1=0,
    delay2=0,
    delay_repump=0,  # arbitrary delays to shutters for ad hoc compensation of small drifts
    delay_shutter_reinitialization=0.1,
):
    """
    Creates an experimental timeline for optical pumping.

    NOTE:
    The AOM is switched off close to, but before, the opening of the first shutter

    WARNING:
    Shutters are reinitialized so that additional optical pumping stages can be added later.
    """

    duration_full = duration_exposition + duration_coil_ramp
    return tl.stack(
        tl.ramp(
            coil__MOT_lower__A=i,
            coil__MOT_upper__A=-i,
            duration=duration_coil_ramp,
            #            fargs={"ti": pt},
        ),
        tl.update(AOM__OP=[[-0.1, 0], [duration_coil_ramp, 1], [duration_full, 0]]),
        tl.update(
            shutter__OP1=[
                [duration_coil_ramp - constants.OP.lag_shutter_on + delay1, 1],
                [delay_shutter_reinitialization, 0],
            ]
        ),
        tl.update(
            shutter__OP2=[
                [duration_full - constants.OP.lag_shutter_off + delay2, 0],
                [delay_shutter_reinitialization, 1],
            ]
        ),
        tl.update(
            shutter__repump=0,
            time=duration_full - constants.lag_repump_shutter + delay_repump,
        ),
        tl.update(AOM__repump=0, time=duration_full),
        tl.anchor(duration_full),
        context="optical_pumping",
    )


def pull_coils(
    duration,
    lower_current,
    upper_current,
    lower_plus_current=0,
    upper_plus_current=0,
    pt=3,
    time=None,
):
    """
    Controls the concentric coil pairs responsible for 'pulling' the atoms.

    It names no context: it inherits the one of the stage it is part of, as
    `magnetic_trapping`'s two calls do.
    """
    return tl.ramp(
        coil__MOT_lower__A=lower_current,
        coil__MOT_upper__A=upper_current,
        coil__MOT_lower_plus__A=lower_plus_current - constants.Compensation.Z__A,
        coil__MOT_upper_plus__A=upper_plus_current + constants.Compensation.Z__A,
        function=lambda origin, terminus, time_resolution: ramp_function.tanh(
            origin, terminus, time_resolution, pt
        ),
        duration=duration,
        time=time,
    )


def magnetic_trapping(
    duration_initial=50e-6,
    lower_current_initial=-1.8,
    upper_current_initial=-1.7,
    duration_strengthen=3e-3,
    lower_current_strengthen=-4.8,
    upper_current_strengthen=-4.7,
):
    """
    Does what it says on the tin.
    """
    return tl.stack(
        pull_coils(
            duration_initial,
            lower_current_initial,
            upper_current_initial,
        ),
        pull_coils(
            duration_strengthen,
            lower_current_strengthen,
            upper_current_strengthen,
            time=duration_initial,
        ),
        tl.anchor(duration_initial + duration_strengthen),
        context="magnetic_trapping",
    )


###########################################################################
#                   Diagnostics                                           #
###########################################################################
# NOTE: Unlike the stages above, which each act on the state the previous one left behind, a diagnostic is *placed*: it can be attached to any named point of an existing timeline, even a finished one, without restructuring it. Its signature says so by declaring `origin`.


def trigger_camera(time, exposure, context, origin):
    """
    Opens the camera for `exposure`, starting `time` after `origin`.

    `origin` has no default, because this stage is placed rather than chained: with one,
    a call that forgot it would fall back on the latest anchor and land wherever the
    timeline happened to end, without an error (maintainer, 2026-10-06).

    `context` is required rather than inherited: a trigger placed into a finished timeline would otherwise adopt the context of its last row at an instant, `finalRamps`, and a camera trigger is not part of the final ramps.

    The camera is not part of the default state, so the timeline it is placed into should set it initially and finally, e.g. `init(trigger__camera=0)` and `finish(trigger__camera=0)`.
    """
    return tl.update(
        trigger__camera=[[time, 1], [time + exposure, 0]],
        context=context,
        origin=origin,
    )


###########################################################################
#                   Stage composition                                     #
###########################################################################

timeline_demo = tl.to_timeline(
    tl.cascade(
        init,
        MOT,
        MOT_detuned_growth,
        molasses,
        optical_pumping,
        magnetic_trapping,
        finish,
        #
        # KW args
        # Basic setup
        init_MOT_ON=True,
        finish_MOT_ON=True,
        # MOT stage
        MOT_duration=15,
        MOT_lower_current=-1.0,
        MOT_upper_current=-0.98,
        # MOT detuned stage
        MOT_detuned_growth_duration=0.1,
        MOT_detuned_growth_duration_ramp=1e-2,
        MOT_detuned_growth_detuning__MHz=-5,  # pt=3,
        # molasses stage
        molasses_duration=4.5e-3,
        molasses_duration_coil_ramp=9e-4,
        molasses_duration_lockbox_ramp=1e-3,
        molasses_to__MHz=-90,
        molasses_delay=-200e-6,
        # OP stage
        optical_pumping_duration_exposition=80e-6,
        optical_pumping_duration_coil_ramp=500e-6,
        optical_pumping_i=-0.12,
        optical_pumping_delay1=-350e-6,
        optical_pumping_delay2=450e-6,
        optical_pumping_delay_repump=0,
        # magnetic trapping stage
        magnetic_trapping_duration_initial=50e-6,
        magnetic_trapping_lower_current_initial=-1.8,
        magnetic_trapping_upper_current_initial=-1.7,
        magnetic_trapping_duration_strengthen=3e-3,
        magnetic_trapping_lower_current_strengthen=-4.8,
        magnetic_trapping_upper_current_strengthen=-4.7,
    )
)

###########################################################################
#                   Running the experiment
###########################################################################

# from wignertime.adwin import core as adwin
#
# wtfile.save(timeline_demo)
# machine = adwin.link_device()
# adwin.upload(timeline_demo, connections, devices, machine, process=1)
# machine.Start_Process(1)

# NOTE:
# ^^^ The above lines are commented out for the sake of automated testing.
#
# `adwin.core` is imported here rather than at the top of the module because it
# requires the optional `ADwin` extra. Importing it at module scope would make
# this demo – and every test that builds a timeline from it – unimportable for
# anyone who installed the package without that extra.
