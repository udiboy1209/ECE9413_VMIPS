CVM
POP SR1
MTCL SR1

LS SR1 SR0 0 # VR1 address
LS SR2 SR0 1 # VR2 address
LS SR3 SR0 2 # VR3 address
LS SR4 SR0 3 # stride
LS SR6 SR0 4 # constant 1

LV VR1 SR1
LV VR2 SR2
LV VR3 SR3

ADDVV VR5 VR2 VR3
SUBVV VR5 VR2 VR3
MULVV VR5 VR2 VR3
DIVVV VR5 VR2 VR3

ADDVS VR5 VR2 SR2
SUBVS VR5 VR2 SR2
MULVS VR5 VR2 SR2
DIVVS VR5 VR2 SR2

SEQVV VR1 VR2
ADDVS VR0 VR0 SR6 # Masked add
SNEVV VR1 VR3
ADDVS VR0 VR0 SR6 # Masked add
SGTVV VR1 VR2
ADDVS VR0 VR0 SR6 # Masked add
SLTVV VR1 VR2
ADDVS VR0 VR0 SR6 # Masked add
SGEVV VR1 VR3
ADDVS VR0 VR0 SR6 # Masked add
SLEVV VR1 VR3
ADDVS VR0 VR0 SR6 # Masked add

SEQVS VR1 SR1
ADDVS VR0 VR0 SR6 # Masked add
SNEVS VR1 SR1
ADDVS VR0 VR0 SR6 # Masked add
SGTVS VR1 SR2
ADDVS VR0 VR0 SR6 # Masked add
SLTVS VR1 SR2
ADDVS VR0 VR0 SR6 # Masked add
SGEVS VR1 SR3
ADDVS VR0 VR0 SR6 # Masked add
SLEVS VR1 SR3
ADDVS VR0 VR0 SR6 # Masked add

CVM

SLL SR6 SR6 SR6 # 1<<1 = 2
SLL SR1 SR1 SR6
SLL SR2 SR2 SR6
SLL SR3 SR3 SR6

SV VR0 SR1
SVWS VR0 SR2 SR4
LVWS VR2 SR2 SR4
SVI VR0 SR3 VR1
LVI VR3 SR3 VR1

HALT