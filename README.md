# VMIPS Simulator

ECE9413 Project

- Meet Udeshi, mdu2004
- Vidyut Singh, vps4038

## Functional simulator

The functional simulator executes the VMIPS program instructions and generates
final state of SRF, VRF, SDMEM, VDMEM after execution.
It also generates an execution trace which is fed to the timing simulator.

### How to run

The functional simulator is located in `functional_sim` folder.
The script must be executed from the **SAME FOLDER** for python to correctly find
all required files.

```
cd functional_sim
python mdu2004_vps4038_funcsimulator.py --iodir <test-dir> [--trace]
```

The optional `--trace` flag, if provided, will generate a `trace.txt` in the
`<test-dir>` folder. This trace is required to execute timing simulator.

## Timing simulator

The timing simulator simulates the data path and control path of the microarchitecture
to generate timing numbers for the program.
It takes in the execution trace from functional simulator, a config for the microarchitecture parameters,
and outputs the number of cycles taken to execute the program.
It can also dump the cycle-wise pipeline state, for debugging and examining the processor.

### How to run

The functional simulator is located in `timing_sim` folder.
The script must be executed from the **SAME FOLDER** for python to correctly find
all required files.
Ensure that the functional simulator is run beforehand with the `--trace` flag
to generate `trace.txt`.

```
cd timing_sim
python mdu2004_vps4038_timingsimulator.py --iodir <test-dir> [--cyclewise]
```

The optional `--cyclewise` flag, if provided, will generate a `cyclewise.log` in the
`<test-dir>` folder. *Note:* This log may be a very large file for long programs.


## Test cases

Tests are present in separate folder inside `tests/`.
Following tests are added:

|Folder|Description|Output|
|------|-----------|------|
|`scalar_isa`| all scalar ISA instructions||
|`vector_isa`| all vector ISA instructions||
|`perf_hazards`| hazard combinations to test the pipeline||
|`perf_loadstore`| vector load store with bank conflicts to test the LS pipeline||
|`dot_prod`| the dot product implementation|`VDMEM @ 2048`|
|`mat_mul_fcc`| the fully connected layer with code for generic sizes|`VDMEM @ 256`|
|`mat_mul_256x256`| the fully connected layer with code specialized for 256x256 size|`VDMEM @ 256`|

The provided `isa` test is kept here, but runs into an infinite loop hence
does not generate outputs.
