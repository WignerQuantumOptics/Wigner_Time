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
' alignment and debugging. Python's side is wignertime.adwin.console, which takes the channels'
' names, conversions and ranges from the same connections and devices as the timelines.
'
' SHADOW STATE, NOT A MAILBOX. Python never waits for this program. It writes the digits it wants
' for a channel into data_51, one word, and returns. Each event below sweeps the channels and
' writes to the hardware only where the wanted digits differ from the ones last written, which it
' keeps in data_52. Repeated writes to one channel therefore coalesce in the data, and there is
' no flag, no handshake and no polling loop that either side could wait on. The mailbox this
' replaced made Python poll a Par until this process had served the previous request. Both
' explanations kept for the fault in which the processor saturated for seconds at a time while the
' console was in use involved that loop (Wigner Time's KNOWN_ISSUES.md, D22).
'
'   data_51[i]   the digits wanted for entry i, written by Python; -2 when unknown
'   data_52[i]   the digits last written for entry i; -1 to write again, -2 when unknown
'   data_53[i]   the module of entry i
'   data_54[i]   the channel of entry i
'   data_55[i]   1 where this process has written entry i since it started, else 0
'   data_56[i]   1 where entry i is a digital line, which takes 0 or 1; 0 where analog
'   par_75       the number of entries; Python sets it to 0 while it rewrites them
'   par_74       hardware writes since this process was started
'   par_77       sweeps since this process was started, as a heartbeat
'   par_76       the value of sequencesFinished (par_18) this process last saw
'
' A sequence stops this process in its lowinit: and, if it was running, starts it again at the
' end of its finish:. Its finish: counts the run in sequencesFinished. When this process starts
' and that count has moved since it last looked, the apparatus holds the run's final state, so it
' ADOPTS it. An entry the final state names takes its digits, in both arrays, so nothing is
' written. An entry it does not name becomes unknown, since it holds whatever the run left it
' at, and nothing is written to it either. Anything Python wanted before or during the run is
' discarded (the maintainer's policy, 2026-09-27). When the count has not moved, it is a start by
' hand, and every entry is written again from data_51, which repairs any disagreement between
' what Python wants and what the hardware holds.
'
' data_55 tells Python which channels hold a value set on the console rather than one a run left
' there: Python warns, before a run, about each analogue channel of that kind that the run will
' jump from its value.

' WHY Priority_Low_Level IS 2, AND MUST STAY ABOVE 1
'
' Wigner Time's sequencer programs (WignerTimeADwin.bas as process 1, WignerTimeADwinADC.bas as
' process 4) stop this console for the length of a run. The first thing their lowinit: does is
' claim the outputs, by setting sequenceOwner (par_17) to their own process number. Only then do
' they call Stop_Process(10). The event: section below tests sequenceOwner before its sweep
' writes anything.
'
' The test and the writes are separate steps, and the priority level decides whether anything
' can come between them. ADwin runs the lowinit: and finish: sections of every process at low
' priority level 1, whatever the process's own priority (ADbasic 6.00 manual, Feb. 2017,
' p. 145). On the T12, a low-priority section at a higher level interrupts one at a lower level
' at any time (pp. 145, 150). Stop_Process completes an event: already under way; it does not
' abandon it (p. 289).
'
' At a level below 1, a sequence that started just after event: had passed its test would
' interrupt the sweep there. The rest of the sweep would then run in the gaps between the run's
' first cycles, and write into the run. At level 2, lowinit: cannot interrupt event:. A sequence
' that starts during a sweep waits until the sweep is done, before any of its own rows. A
' sequence that has already claimed the outputs makes the test fail. Either way, nothing reaches
' the outputs during a run. The sweep is bounded, at most maxWritesPerSweep hardware writes and
' one comparison per entry, so the wait is short.
'
' The price is that event: may interrupt the lowinit: or finish: of any process, and any
' low-priority process at level 1 or below. High-priority sections, the sequencers' init: and
' event: among them, still interrupt it at any time, and so does communication with the PC.
'
' Not yet checked on the rig: open this file in the ADbasic IDE, confirm that Process Options
' shows level 2, then compile and load. Recorded as D22 in Wigner Time's KNOWN_ISSUES.md, and as
' L23 in the lab's.

#include ADwinPro_All.Inc

' sequenceOwner, sequencesFinished, the final-state arrays, and the rest of the sequencers'
' contract. It must stay in this file's directory.
#include .\WignerTimeSequencer.inc

#define consoleMaxEntries 512
#define maxWritesPerSweep 8
#define reassertDigits -1
#define unknownDigits -2

#define writesTotal par_74
#define entryCount par_75
#define sequencesSeen par_76
#define sweeps par_77

dim data_51[consoleMaxEntries] as long ' digits wanted, written by Python; -2 unknown
dim data_52[consoleMaxEntries] as long ' digits last written; -1 to write again, -2 unknown
dim data_53[consoleMaxEntries] as long ' module of each entry
dim data_54[consoleMaxEntries] as long ' channel of each entry
dim data_55[consoleMaxEntries] as long ' 1 where written since this process started
dim data_56[consoleMaxEntries] as long ' 1 where the entry is digital, 0 where analog

dim i, f, digits, writes as long

init:
  sweeps = 0 : writesTotal = 0
  for i = 1 to entryCount
    data_55[i] = 0
    ' Every port of the module of each digital entry an output (D18).
    if (data_56[i] = 1) then p2_digprog(data_53[i],1111b)
  next i

  if (sequencesFinished <> sequencesSeen) then
    ' A sequence has finished since this process last looked: adopt its final state.
    for i = 1 to entryCount
      data_51[i] = unknownDigits : data_52[i] = unknownDigits
      if (data_56[i] = 1) then
        for f = 1 to digitalFinishDim
          if ((data_41[f] = data_53[i]) and (data_42[f] = data_54[i])) then
            data_51[i] = data_43[f] : data_52[i] = data_43[f]
          endif
        next f
      else
        for f = 1 to analogFinishDim
          if ((data_31[f] = data_53[i]) and (data_32[f] = data_54[i])) then
            data_51[i] = data_33[f] : data_52[i] = data_33[f]
          endif
        next f
      endif
    next i
    sequencesSeen = sequencesFinished
  else
    ' A start by hand: write every entry again from what Python wants.
    for i = 1 to entryCount
      data_52[i] = reassertDigits
    next i
  endif

event:
  inc sweeps
  ' Nothing is written while a sequence owns the outputs. A sequence started during this
  ' sweep waits for it: see the head of this file.
  if (sequenceOwner = 0) then
    writes = 0
    for i = 1 to entryCount
      digits = data_51[i]
      if ((digits >= 0) and (digits <> data_52[i]) and (writes < maxWritesPerSweep)) then
        if (data_56[i] = 1) then
          if (digits = 0) then
            p2_digout(data_53[i],data_54[i],0)
          else
            p2_digout(data_53[i],data_54[i],1)
          endif
        else
          p2_dac(data_53[i],data_54[i],digits)
        endif
        ' What was asked for, not a clamped value: a request the hardware cannot take exactly
        ' would otherwise differ from data_52 on every sweep, and be written for ever.
        data_52[i] = digits
        data_55[i] = 1
        inc writes
        inc writesTotal
      endif
    next i
  endif
