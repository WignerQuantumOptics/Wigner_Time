'<ADbasic Header, Headerversion 001.001>
' Process_Number                 = 4
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

''''''''''''''''''''''''''''''''''''
' definitions for ADC
''''''''''''''''''''''''''''''''''''
' The recording window, written by Python (wignertime.adwin.adc.arm) in cycles of the run, so
' that nothing here depends on the cycle period: the burst starts at ADC_StartCycle and is over
' by ADC_EndCycle. finish: resets ADC_EndCycle to 0, so a window is armed for one run only.
' FPar_62, the start in seconds, is no longer read.
#Define ADC_StartCycle Par_42
#Define ADC_EndCycle Par_43
#Define ADC_Duration FPar_61 ' in s

' Reported to Python: how many samples were recorded (0 unless the burst had its whole window),
' and how far apart they are, in whole ns, since an FPar would reach Python in single precision.
#Define ADC_DataAmount Par_41
#Define ADC_SamplePeriod Par_44 ' in ns

#Define ADC_Card 2
#Define ADC_Channel 1

#Define ADC_Pulses 25 ' Minimum for 16bit cards
#Define ADC_MaxDataAmount 67108860
#Define ADC_TimeInterval 0.25 ' (ADC_Pulses*0.01) in us
''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''


Dim i, ADC_ChannelPattern, startADC, endADC As Long
Dim Data_1[ADC_MaxDataAmount] As Long

'dim cyclecount, analogIdx, digitalIdx as long

lowinit:
  ' The outputs are the sequence's from here on. Claimed before the console is stopped: a
  ' stopped process normally runs its event: once more, and the console writes nothing while
  ' sequenceOwner is nonzero.
  sequenceOwner = 4
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
    
  For i=1 To ADC_MaxDataAmount
    Data_1[i]=0
  Next i

  P2_DigProg(1,1111b) ' set all the digital ports to output
  
  ' configuring ADC burst mode
  ADC_DataAmount=1000000*ADC_Duration/ADC_TimeInterval
  If (ADC_DataAmount > ADC_MaxDataAmount) Then ADC_DataAmount = ADC_MaxDataAmount
  ADC_SamplePeriod=ADC_TimeInterval*1000
  ' Armed only if the window has a positive length and closes within the run. Otherwise the
  ' burst is never started, and finish: records nothing.
  startADC=ADC_StartCycle
  endADC=ADC_EndCycle
  If ((startADC < 0) Or (endADC <= startADC) Or (endADC > endCC)) Then startADC=-1
  ADC_ChannelPattern=Shift_Left(1,ADC_Card-1)
  
  P2_Set_Average_Filter(ADC_Card,0) 'sets the module, where the data  is happening, and also how many values does it use for the average
  P2_Burst_Init (ADC_Card, ADC_Channel, 0, ADC_DataAmount, ADC_Pulses, 0)
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
  par_10=1

  If ( (cyclecount = startADC) ) Then P2_Burst_Start (ADC_ChannelPattern)

  'If ( (cyclecount = endADC + 10) ) Then End
  
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
  
  ' The samples, only if the burst had its whole window. A run that was not armed, was stopped
  ' before endADC, or was refused by the period check (endCC = -1) reports none.
  If ((startADC >= 0) And (cyclecount > endADC)) Then
    P2_Burst_Read_Unpacked1 (ADC_Card, ADC_DataAmount, 0, Data_1, 1, 3)
  Else
    ADC_DataAmount = 0
  EndIf
  ' Armed for one run only.
  ADC_EndCycle = 0

  ' Last of all, once the final state is out: the arrays are free.
  sequenceOwner = 0

  ' And the console, if the run stopped it, comes back on the final state.
  if (consoleWasRunning = 1) then Start_Process(consoleProcess)
