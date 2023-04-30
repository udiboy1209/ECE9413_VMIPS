# This version hardcodes for 256x256
CVM               #clear mask
POP SR1           #SR1 contains MVL = 64
###
#SR0 and VR0 are 0 on reset
LS SR3 SR0 1      #SR3 contains start address for W = 512
LS SR6 SR0 2      #SR6 contains matrix num rows = 256
LS SR4 SR0 3      #SR4 contains start address for temp output = 66048
LS SR7 SR0 0      #SR7 contains 1
ADD SR5 SR1 SR7   #SR5 contains temp output offset 64+1=65

# Load input into 4 vector registers
LV VR1 SR0
ADD SR0 SR0 SR1 # +64
LV VR2 SR0
ADD SR0 SR0 SR1 # +64
LV VR3 SR0
ADD SR0 SR0 SR1 # +64
LV VR4 SR0
XOR SR0 SR0 SR0 # clear

###MATRIX MUL LOOP
ADDVV VR5 VR0 VR0 # VR5 stores result
LV VR6 SR3 # VR6 stores weight
ADD SR3 SR3 SR1 # +64
MULVV VR7 VR6 VR1
LV VR6 SR3 # Load next 64 weights
ADD SR3 SR3 SR1 # +64
ADDVV VR5 VR5 VR7
MULVV VR7 VR6 VR2
LV VR6 SR3
ADD SR3 SR3 SR1 # +64
ADDVV VR5 VR5 VR7
MULVV VR7 VR6 VR3
LV VR6 SR3
ADD SR3 SR3 SR1 # +64
ADDVV VR5 VR5 VR7
MULVV VR7 VR6 VR4
ADDVV VR5 VR5 VR7
SUB SR6 SR6 SR7
SV VR5 SR4 # Store temp
ADD SR4 SR4 SR5 # +65
BGT SR6 SR0 -20 # Loop back
###MATRIX MUL LOOP DONE

LS SR4 SR0 3      #SR4 contains start address for temp output
LS SR2 SR0 4      #SR2 contains number of vecs in one row = 4

###REDUCE OUTER LOOP = 4
ADD SR6 SR1 SR0   #SR6 contains ... = 64
ADDVV VR5 VR0 VR0 # VR5 stores result

###REDUCE INNER LOOP = 64
LVWS VR6 SR4 SR5
ADDVV VR5 VR5 VR6
SUB SR6 SR6 SR7
ADD SR4 SR4 SR7
BGT SR6 SR0 -4

LS SR3 SR0 2
LV VR6 SR3 # Load bias
ADDVV VR5 VR5 VR6 # Add bias
SV VR5 SR3 # Store output
ADD SR3 SR3 SR1
SS SR3 SR0 2
LS SR3 SR0 5      #SR3 contains offset to next vec = 64*64 = 4096
ADD SR4 SR4 SR3
SUB SR2 SR2 SR7
BGT SR2 SR0 -16

HALT
