' What the two sequencer programs share, WignerTimeADwin.bas (process 1) and
' WignerTimeADwinADC.bas (process 4): the Par numbers of their contract with
' wignertime.adwin.core.upload, the global arrays they play, and the subroutine that plays them.
'
' Global arrays used by several processes must be declared identically in each (ADbasic 6.00
' manual, p. 148), and both programs play the same arrays, so they are declared here, once.
' A change here is a change to the contract with Python: the array sizes are
' wignertime.adwin.ROWS__MAX, and the Par numbers are the PAR__ constants beside it.
'
' The programs include this file by a path relative to their own, .\WignerTimeSequencer.inc,
' so it must stay in their directory. Should they become members of an ADbasic project, the path
' is taken relative to the project file instead (p. 229).

#define endCC par_1
#define analogArrayDim par_2
#define digitalArrayDim par_3

#define analogMaxArrayDim 10000000
#define digitalMaxArrayDim 10000

#define cyclecount par_6
#define analogIdx par_7
#define digitalIdx par_8

' The period check (#128). `upload` writes the Processdelay it built the arrays for into
' processdelayExpected; this program reports the one its event loop runs at.
#define processdelayExpected par_9
#define processdelayReported par_14

' The final state (B11), in arrays of its own, played in full by finish: however the run
' ended. At most one row per variable, so a few hundred entries suffice.
#define finishMaxArrayDim 256
#define analogFinishDim par_15
#define digitalFinishDim par_16

' Who is playing the arrays (step 9): this process's number from the start of lowinit to the
' end of finish:, 0 otherwise. The arrays are shared by every process on the machine, so
' Python waits on whichever process holds them, and the console writes nothing meanwhile.
#define sequenceOwner par_17
#define consoleProcess 10
' The console's own status, 1 while it runs, 0 when stopped or not loaded, -1 while being
' stopped. ADbasic takes the process number as part of the name, so it is written twice here
' and the two must agree.
#define consoleRunning Process10_Running
' How many sequences have finished since the machine was booted, counted at the end of every
' finish:. The console compares it with the count it last saw when it starts: if a sequence has
' finished since, the apparatus holds that run's final state, and the console adopts it rather
' than re-asserting what it held before the run.
#define sequencesFinished par_18


sub processUpdates(cc)
  ' analog
  if ( (analogIdx <= analogArrayDim) and (data_10[analogIdx] = cc) ) then
    do  
      p2_dac(data_11[analogIdx],data_12[analogIdx],data_13[analogIdx])
      '      par_10=data_10[analogIdx] : par_11=data_11[analogIdx] : par_12=data_12[analogIdx] : par_13=data_13[analogIdx]
      inc analogIdx
    until ( (analogIdx > analogArrayDim) or (data_10[analogIdx] > cc) )
  endif
  ' digital
  if ( (digitalIdx <= digitalArrayDim) and (data_20[digitalIdx] = cc) ) then
    do
      p2_digout(1,data_22[digitalIdx],data_23[digitalIdx])
      '      par_20=data_20[digitalIdx] : par_22=data_22[digitalIdx] : par_23=data_23[digitalIdx]
      inc digitalIdx
    until ( (digitalIdx > digitalArrayDim) or (data_20[digitalIdx] > cc) )
  endif
endsub


dim data_10[analogMaxArrayDim] as long ' Clock cycles of analog updates
dim data_11[analogMaxArrayDim] as long ' Module numbers of analog updates
dim data_12[analogMaxArrayDim] as long ' Channels of analog updates
dim data_13[analogMaxArrayDim] as long ' Values (digitized) of analog updates

dim data_20[digitalMaxArrayDim] as long ' Clock cycles of digital updates
dim data_22[digitalMaxArrayDim] as long ' Channels of digital updates
dim data_23[digitalMaxArrayDim] as long ' Values (0 or 1) of digital updates

dim data_31[finishMaxArrayDim] as long ' Module numbers of the final analog state
dim data_32[finishMaxArrayDim] as long ' Channels of the final analog state
dim data_33[finishMaxArrayDim] as long ' Values (digitized) of the final analog state

dim data_42[finishMaxArrayDim] as long ' Channels of the final digital state
dim data_43[finishMaxArrayDim] as long ' Values (0 or 1) of the final digital state

dim finishIdx as long
dim consoleWasRunning as long
