CVM

LS SR1 SR0 0 # VR1 address
LS SR2 SR0 1 # VR2 address
LS SR3 SR0 2 # VR3 address
LS SR4 SR0 3 # stride
LS SR6 SR0 4 # constant 1

# Aligned
LV VR1 SR1
# Unaligned
SV VR0 SR3

# Stride 4
LVWS VR2 SR2 SR4

# Stride 5
ADD SR4 SR4 SR6
LVWS VR2 SR2 SR4

# Gather from odd address
LVI VR3 SR3 VR1

HALT
