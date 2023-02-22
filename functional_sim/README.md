VMIPS Functional Simulator
==========================

ECE9413 Project Part1

- Meet Udeshi, mdu2004
- Vidyut Singh, vps4038

Running
=======

The file `mdu2004_vps4038_funcsimulator.py` is the entry point.
Rest of the components are spread across different files.
The script needs to be run from the same folder.

Test cases
==========

Tests are present in separate folder inside `tests/`.
Following tests are added:

 - `scalar_isa`: tests all scalar ISA instructions
 - `vector_isa`: tests all vector ISA instructions
 - `dot_prod`: tests the dot product implementation

The dot product is implemented in `tests/dot_prod/Code.asm`.
The output dot product is written at location 2048 in the VDMEM.

The provided `isa` test is kept here, but runs into an infinite loop hence
does not generate outputs.
