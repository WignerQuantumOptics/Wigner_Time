'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 1
' Initial_Processdelay           = 5000
' Eventsource                    = Timer
' Control_long_Delays_for_Stop   = No
' Priority                       = High
' Version                        = 1
' ADbasic_Version                = 6.3.1
' Optimize                       = Yes
' Optimize_Level                 = 1
' Stacksize                      = 1000
' Info_Last_Save                 = DESKTOP-PB9TKB9  DESKTOP-PB9TKB9\User
'<Header End>
#include ADwinPro_All.Inc

' The contract with Python and the arrays, shared with the other sequencer program.
#include .\WignerTimeSequencer.inc


lowinit:
  ' The outputs are the sequence's from here on. Claimed before the console is stopped: a
  ' stopped process normally runs its event: once more, and the console writes nothing while
  ' sequenceOwner is nonzero.
  sequenceOwner = 1
  ' The manual console must not write to the outputs while a sequence plays. Only a console
  ' that is running now is started again after the run; one already being stopped, from the
  ' PC or by another process, is not. The console runs at low priority level 2, above the
  ' level 1 of this section, so an event: of it already under way has finished before this
  ' section began (KNOWN_ISSUES.md, D22).
  consoleWasRunning = consoleRunning
  Stop_Process(consoleProcess)
  cyclecount = 0 : analogIdx = 1 : digitalIdx = 1
  par_4 = analogMaxArrayDim
  par_5 = digitalMaxArrayDim
  p2_digprog(1,1111b) ' set all the digital ports to output
  
  processUpdates(-2)
  
init:
  processUpdates(-1)

  ' Checked here rather than in lowinit, since a program may set its own Processdelay
  ' before this point. On a mismatch the first event ends the run: the initial state has
  ' been applied, and nothing after it is played.
  processdelayReported = Processdelay
  if (processdelayReported <> processdelayExpected) then endCC = -1
  
event:
  if (cyclecount > endCC) then end
  
  processUpdates(cyclecount)
  
  inc cyclecount

finish:
  ' Unconditionally, from index 1: an interrupted run restores the final state as surely as
  ' one that completed, which the playback arrays could not guarantee (B11).
  for finishIdx = 1 to analogFinishDim
    p2_dac(data_31[finishIdx],data_32[finishIdx],data_33[finishIdx])
  next finishIdx
  for finishIdx = 1 to digitalFinishDim
    p2_digout(1,data_42[finishIdx],data_43[finishIdx])
  next finishIdx

  ' Last of all, once the final state is out: the run is counted, and the arrays are free.
  inc sequencesFinished
  sequenceOwner = 0

  ' And the console, if the run stopped it, comes back on the final state.
  if (consoleWasRunning = 1) then Start_Process(consoleProcess)
