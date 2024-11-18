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

''''''''''''''''''''''''''''''''''''
' definitions for ADC
''''''''''''''''''''''''''''''''''''
#Define ADC_DataAmount Par_41

#Define ADC_Duration FPar_61 ' in s
#Define ADC_ON_Time FPar_62 ' in s

#Define ClockInterval 5 ' in us
#Define ADC_Card 2
#Define ADC_Channel 1

#Define ADC_Pulses 25 ' Minimum for 16bit cards
#Define ADC_MaxDataAmount 67108860
#Define ADC_TimeInterval 0.25 ' (ADC_Pulses*0.01) in us
''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''


#define endCC par_1
#define analogArrayDim par_2
#define digitalArrayDim par_3

#define analogMaxArrayDim 10000000
#define digitalMaxArrayDim 10000

#define cyclecount par_6
#define analogIdx par_7
#define digitalIdx par_8

Dim i, ADC_ChannelPattern, startADC, endADC As Long

Dim Data_1[ADC_MaxDataAmount] As Long


sub processSwitches(cc)
  ' analog
  if (data_10[analogIdx] = cc) then
    do  
      p2_dac(data_11[analogIdx],data_12[analogIdx],data_13[analogIdx])
      '      par_10=data_10[analogIdx] : par_11=data_11[analogIdx] : par_12=data_12[analogIdx] : par_13=data_13[analogIdx]
      inc analogIdx
    until ( (analogIdx > analogArrayDim) or (data_10[analogIdx] > cc) )
  endif
  ' digital
  if (data_20[digitalIdx] = cc) then
    do
      p2_digout(1,data_22[digitalIdx],data_23[digitalIdx])
      '      par_20=data_20[digitalIdx] : par_22=data_22[digitalIdx] : par_23=data_23[digitalIdx]
      inc digitalIdx
    until ( (digitalIdx > digitalArrayDim) or (data_20[digitalIdx] > cc) )
  endif
endsub


dim data_10[analogMaxArrayDim] as long ' Clock cycles of analog switches
dim data_11[analogMaxArrayDim] as long ' Module numbers of analog switches
dim data_12[analogMaxArrayDim] as long ' Channels of analog switches
dim data_13[analogMaxArrayDim] as long ' Values (digitized) of analog switches

dim data_20[digitalMaxArrayDim] as long ' Clock cycles of digital switches
dim data_22[digitalMaxArrayDim] as long ' Channels of digital switches
dim data_23[digitalMaxArrayDim] as long ' Values (0 or 1) of digital switches

'dim cyclecount, analogIdx, digitalIdx as long

lowinit:
  cyclecount = 0 : analogIdx = 1 : digitalIdx = 1
  par_4 = analogMaxArrayDim
  par_5 = digitalMaxArrayDim
  p2_digprog(1,1111b) ' set all the digital ports to output
  
  processSwitches(-2)
    
  For i=1 To ADC_MaxDataAmount
    Data_1[i]=0
  Next i

  P2_DigProg(1,1111b) ' set all the digital ports to output
  
  ' configuring ADC burst mode
  ADC_DataAmount=1000000*ADC_Duration/ADC_TimeInterval
  If (ADC_DataAmount > ADC_MaxDataAmount) Then ADC_DataAmount = ADC_MaxDataAmount
  startADC=ADC_ON_Time*1.0e6/ClockInterval+1
  endADC=startADC+ADC_Duration*1.0e6/ClockInterval
  ADC_ChannelPattern=Shift_Left(1,ADC_Card-1)
  
  P2_Set_Average_Filter(ADC_Card,0) 'sets the module, where the data  is happening, and also how many values does it use for the average
  P2_Burst_Init (ADC_Card, ADC_Channel, 0, ADC_DataAmount, ADC_Pulses, 0)
init:
  processSwitches(-1)

event:
  if (cyclecount = endCC+1) then end '+1 is needed to resolve the indexing differences between ADwin and Python
  
  processSwitches(cyclecount)
  par_10=1

  If ( (cyclecount = startADC) ) Then P2_Burst_Start (ADC_ChannelPattern)

  'If ( (cyclecount = endADC + 10) ) Then End
  
  inc cyclecount

finish:
  processSwitches(2147483647) ' 2**31-1
  
  P2_Burst_Read_Unpacked1 (ADC_Card, ADC_DataAmount, 0, Data_1, 1, 3)
