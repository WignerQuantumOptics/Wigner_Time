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

#define endCC par_1
#define analogArrayDim par_2
#define digitalArrayDim par_3

#define analogMaxArrayDim 10000000
#define digitalMaxArrayDim 10000

#define cyclecount par_6
#define analogIdx par_7
#define digitalIdx par_8


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


lowinit:
  cyclecount = 0 : analogIdx = 1 : digitalIdx = 1
  par_4 = analogMaxArrayDim
  par_5 = digitalMaxArrayDim
  p2_digprog(1,1111b) ' set all the digital ports to output
  
  processUpdates(-2)
  
init:
  processUpdates(-1)
  
event:
  if (cyclecount > endCC) then end
  
  processUpdates(cyclecount)
  
  inc cyclecount

finish:
  processUpdates(2147483647) ' 2**31-1

