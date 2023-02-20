//SR0 contains scalar value "0",
//VR0 contains vector value "0",
//SR2 contains (length of vector)%MVL = 2,
//SR3 contains length of vector = 450,
//SR4 contains start address for A,
//SR5 contains start address for B,
//SR6 contains the address to final result = 2048,
//SR7 contains scalar value "1"

CVM                 //clear mask
POP SR1             //SR1 contains MVL = 64
MTCL SR2            //change vector length to mod value
LV VR1, SR4         //load starting elements of A
LV VR2, SR5         //load starting elements of B
MULVV VR3, VR1, VR2 //VR3 = VR1*VR2 (C=A*B)
ADD SR4, SR4, SR2   //update address to next set of elements of A
ADD SR5, SR5, SR2   //update address to next set of elements of B
SUB SR3, SR3, SR2   //update count of elements remaining
MTCL SR1

Loop1:              //start loop to multiply remaining elements
LV VR1, SR4         
LV VR2, SR5         
MULVV VR4, VR1, VR2 
ADDVV VR3, VR3, VR4 //add elements to VR3      
ADD SR4, SR4, SR1   
ADD SR5, SR5, SR1   
SUB SR3, SR3, SR1   //decrement loop
BGT SR3, SR0, Loop1 //stay in loop if elements remain

Loop2:              //start loop to add elements of VR3 together
SV VR3, SR6         //store VR3 to SR6
SLL SR3, SR3, SR7   //divide SR3 by 2
MTCL SR3            //set vector length = SR3/2
LV VR3, SR6
ADD SR8, SR6, SR3
LV VR4, SR8         //splitting vectors into half
ADDVV VR3, VR3, VR4 //adding each half together
BGT SR3, SR0, Loop2 //stay in loop till vector length is 1

SV VR3 SR6          //store final result to location 2048
