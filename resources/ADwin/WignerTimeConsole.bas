'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 10
' Initial_Processdelay           = 100000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = Low
' Priority_Low_Level             = 2
' Version                        = 1
' ADbasic_Version                = 6.3.1
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DESKTOP-PB9TKB9  DESKTOP-PB9TKB9\User
'<Header End>

' The manual console: direct access to the apparatus's channels while no sequence plays, for
' alignment and debugging. Python's side is wignertime.adwin.console, which writes one request
' at a time and reads the channels' names, conversions and ranges from the same connections and
' devices as the timelines. The contract:
'
'   par_70, par_71, par_72   module, channel and digits of a request (module 1 is digital)
'   par_73                   nonzero while a request waits; cleared here once it is served
'   par_74                   requests served since this process was started
'   par_17                   sequenceOwner, from WignerTimeSequencer.inc: nonzero while a
'                            sequence owns the outputs
'
' A sequence stops this process in its lowinit: and, if it was running, starts it again at the
' end of its finish:, when the apparatus holds the run's final state. A request made in the
' meantime is discarded: Python refuses one while sequenceOwner is nonzero, and init: below
' drops one that was written in the instant before the sequence took the outputs.

' WHY Priority_Low_Level IS 2, AND MUST STAY ABOVE 1
'
' Wigner Time's sequencer programs (WignerTimeADwin.bas as process 1, WignerTimeADwinADC.bas as
' process 4) stop this console for the length of a run and start it again afterwards. The first
' thing their lowinit: does is claim the outputs, by setting sequenceOwner (par_17) to their own
' process number. Only then do they call Stop_Process(10). The event: section below tests
' sequenceOwner before it writes, so a request made while a sequence owns the outputs waits until
' the sequence has finished.
'
' The test and the write are two steps, and the priority level decides whether anything can come
' between them. ADwin runs the lowinit: and finish: sections of every process at low priority
' level 1, whatever the process's own priority (ADbasic 6.00 manual, Feb. 2017, p. 145). On the
' T12, a low-priority section at a higher level interrupts one at a lower level at any time
' (pp. 145, 150).
'
' At the level this console had before, -5, a sequence that started just after event: had passed
' its test interrupted event: between the test and the write. Its lowinit: claimed the outputs
' and stopped the console. But Stop_Process completes an event: already under way; it does not
' abandon it (p. 289). The rest of that event: then ran in the gaps between the run's first
' cycles, and wrote the requested value into the run. The value stayed there until the timeline
' next changed that channel, and nothing reported it.
'
' At level 2, lowinit: cannot interrupt event:. A sequence that starts while event: is serving a
' request waits until the write is done, before any of its own rows. A sequence that has already
' claimed the outputs makes the test fail. Either way, nothing reaches the outputs during a run.
'
' The price is that event: may now interrupt the lowinit: or finish: of any process, and any
' low-priority process at level 1 or below. It is a handful of instructions every Processdelay,
' and a single comparison when nothing has been requested. High-priority sections, the
' sequencers' init: and event: among them, still interrupt it at any time, and so does
' communication with the PC.
'
' Not yet checked on the rig: open this file in the ADbasic IDE, confirm that Process Options
' shows level 2, then compile and load. Recorded as D22 in Wigner Time's KNOWN_ISSUES.md, and as
' L23 in the lab's.

#include ADwinPro_All.Inc

' sequenceOwner, and the rest of the sequencers' contract. It must stay in this file's directory.
#include .\WignerTimeSequencer.inc

#define moduleToSwitch par_70
#define channelToSwitch par_71
#define digitToSwitch par_72
#define flag par_73 ' when nonzero, it signifies that there is something to actuate
#define diagnostics par_74

dim moduleBefore, channelBefore, digitBefore as long

init:
  ' A request left from before this start is dropped, whoever started it. After a sequence it
  ' was made during the run, and the final state is what the apparatus is to hold.
  flag=0
  moduleBefore=0 : channelBefore=0 : digitBefore=0
  
  diagnostics=0

  p2_digprog(1,1111b) ' set all the digital ports to output
  
event:
  ' No request is served while a sequence owns the outputs. A sequence started between this
  ' test and the write below waits for the write: see the head of this file.
  if ( (flag <> 0) and (sequenceOwner = 0) ) then
    inc diagnostics
    if ( moduleToSwitch=1 ) then
      if ( digitToSwitch=0 ) then
        p2_digout(1,channelToSwitch,0)
      else
        p2_digout(1,channelToSwitch,1)
      endif
    else
      p2_dac(moduleToSwitch,channelToSwitch,digitToSwitch)
    endif
    flag=0 : moduleBefore=moduleToSwitch : channelBefore=channelToSwitch : digitBefore=digitToSwitch
  endif
