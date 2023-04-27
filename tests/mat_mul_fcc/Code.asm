CVM               #clear mask
POP SR1           #SR1 contains MVL = 64
###
#SR0 and VR0 are 0 on reset
###MATRIX MUL LOOP
LS SR3 SR0 1      #SR3 contains start address for W = 512
LS SR4 SR0 2      #SR4 contains length of output vector = 256
LS SR5 SR0 3      #SR5 contains address to store result before bias addition = 66048
###DOT PRODUCT LOOP
LS SR6 SR0 4      #SR6 contains length of input vector = 256
LS SR7 SR0 5      #SR7 contains start address for A = 0
MTCL SR1	  #set vector length to MVL
ADDVV VR1 VR0 VR0 #set result register VR1 to 0
#start loop to multiply elements
BGE SR6 SR1 +3	  #if vector elements remaining < MVL, change vector length
SUB SR2 SR1 SR6
MTCL SR2
LV VR2 SR7        #load starting elements of A
LV VR3 SR3        #load starting elements of W
MULVV VR4 VR2 VR3 #VR4 = VR2*VR3 (C=A*W)
ADDVV VR1 VR1 VR4 #add elements to VR1      
ADD SR7 SR7 SR1   
ADD SR3 SR3 SR1   
SUB SR6 SR6 SR1   #update count of elements remaining
BGT SR6 SR0 -10   #stay in loop if elements remain
###
MTCL SR1
ADD SR7 SR1 SR0	  #set vector length to MVL
LS SR2 SR0 0      #SR2 contains scalar value "1"
#start loop to add elements of VR1 together
SV VR1 SR5        #store VR1 to SR5
SRL SR7 SR7 SR2   #divide SR7 by 2
MTCL SR7          #set vector length = SR7/2
LV VR1 SR5
ADD SR6 SR5 SR7
LV VR4 SR6        #splitting vectors into half
ADDVV VR1 VR1 VR4 #adding each half together
BGT SR7 SR2 -7    #stay in loop till vector length is 1
###
SV VR1 SR5        #store final result to location 66048
ADD SR5 SR5 SR2	  #increment to next address location
###END DOT PRODUCT
SUB SR4 SR4 SR2   #update count of W matrix columns
BGT SR4 SR0 -29   #stay in loop if columns remain
##END MATRIX MUL
#start loop to add bias
LS SR7 SR0 3      #SR7 contains start address to fetch/store result (R) = 66048
LS SR6 SR0 2      #SR6 contains length of output vector = 256
LS SR3 SR0 6      #SR3 contains start address of B = 256
MTCL SR1	  #set vector length to MVL
#start loop to add elements
BGE SR6 SR1 +3	  #if vector elements remaining < MVL, change vector length
SUB SR2 SR1 SR6
MTCL SR2
LV VR2 SR7        #load starting elements of R
LV VR3 SR3        #load starting elements of B
ADDVV VR1 VR2 VR3 #VR4 = VR2+VR3 (Y=R+B)
SV VR1 SR7	  #store back to result address
ADD SR7 SR7 SR1   
ADD SR3 SR3 SR1   
SUB SR6 SR6 SR1   #update count of elements remaining
BGT SR6 SR0 -10   #stay in loop if elements remain
###
