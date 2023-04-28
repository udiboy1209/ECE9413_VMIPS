CVM # busy VMR
POP SR1 # busy SR1
MTCL SR1 # busy VRL
ADDVV VR2 VR2 VR3 # Should wait for MTCL

LS SR1 SR0 0 # busy SR1
ADD SR0 SR0 SR0 # WAR hazard

SUBVV VR5 VR6 VR7 # No hazard
MULVV VR6 VR2 VR3 # WAR hazard
SUBVV VR0 VR5 VR6 # RAW hazard

ADD SR2 SR1 SR1 # No hazard
MULVS VR5 VR2 SR2 # RAW hazard with scalar

SEQVV VR1 VR1 # no hazard, busy VMR
DIVVS VR0 VR7 SR6 # RAW hazard on VMR
MTCL SR2 # No hazard, busy VLR
MULVV VR3 VR1 VR1 # RAW hazard

MTCL SR2 # WAR hazard, busy VLR
MFCL SR3 # RAW hazard

SEQVV VR1 VR1 # no hazard, busy VMR
CVM # WAW hazard on VMR

HALT
