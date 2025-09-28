# 1. Introduction

The scope of this package are prototype iterative numerical algorithms, such as ODE solvers, root finding algorithms,
etc...  This package should provide ballpark indications of the total cost related to floating-point calculations of
such prototypes before they are implemented in a compiled language. Secondly, we restrict ourselves to relatively
recent 64-bit processors (released in last 5-10 years max).  This has repercussions on which instructions we should
focus on when inspecting FPU spec sheets or interpreting external analyses.

## 1.1. ISA families

We limit ourselves to x86 (notably x64/amd64) and arm (notably v8 or higher) processors.  Other types, such as 
Intel Itanium, Transmeta, IBM Power... chips can be considered either obsolete or sufficiently niche. 

## 1.2. Scalar vs Vector instructions

Given the nature of algorithms we intend to analyze, the type of math code typically consists of a mix of instructions,
forming dependent chains of operations, that lead to choices (strategy, terminate, ...) made in each iteration.  This
type of code does not lend itself to being easily vectorized, hence we ignore vector instructions:
- **x86**: SSE2/3/4 vector instructions, AVX<n>, ...
- **arm**: SVE, SME, NEON, ... 

## 1.3. 64-bit instruction sets

More specifically, this means that for x86 CPUs we need to focus on scalar SSE2 instructions, rather than the still-supported
but rarely used 32-bit-era x87 instructions.

For ARM processors, we should focus on arm v8-A or higher (AARCH64/ARM64).

## 1.4. Latency types

For most processors, two instruction latency figures can typically be obtained (*naming varies*):
- **execution latency**: time needed for end-to-end execution until a new instruction can start using the end result
- **(reciprocal) throughput**: time needed per instruction with maximal throughput for independent similar operations

Given the nature of code we intend to analyze, we focus on **execution latency**, i.e. the full end-to-end latency.

## 1.5. Benchmark setup

In case we want to benchmark FPU instructions, we need to make sure we are not limited by memory bandwidth, but truly
measure the inherent floating-point capabilities of a CPU.  Therefore we should make sure all data fits in L1 (data) cache.

For all aforementioned classes of CPUs, L1 (data) cache is at least 32KB in size.  Hence, we should limit any benchmark
to work with a maximum of 4K double precision values.


# 2. Sources

We will focus on 3 types of sources for FPU instruction 'cost':
* **benchmarks**: these are the benchmarks implemented in this package; these can be run on each CPU architecture that is 
  supported by numba and can analyze each type of math operation, even those that have no hardware support in some or all cpu architectures.
* **external - analyses**: CPU latency numbers obtained by 3rd parties by running tailored benchmarks / analyses; limited to what can be publicly found.
* **external - spec sheets**: Official vendor spec sheets; limited to what can be publicly found (e.g. Apple does not disclose this info) and 
  those instructions that have hardware support.

Given the mentioned PROs & CONs, these 3 sources can be considered complementary, and we can expect them to provide a balanced holistic picture.

# 3. Instruction Mappings

The table below shows the mapping between math operations & FPU instructions for different architectures.  
x87 instructions are provided fyi; for x86 CPUs only SSE2 scalar instructions are considered. 

| math        | x87                           | SSE2           | ARM v8/9 |
|-------------|-------------------------------|----------------|----------|
| abs(x)      | FABS                          | ANDPD (1)      | FABS     |
| double->int | FRND                          | CVTSD2SI       | FCVTZS   | 
| int->double | ?                             | CVTSI2SD       | SCVTF    |
| -x          | FCHS                          | XORPD (1)      | FNEG     |
| x > 0       | FTST                          | (U)COMISD (2)  | FCMP     |
| x == 0      | FTST                          | (U)COMISD (2)  | FCMP     |
| x < 0       | FTST                          | (U)COMISD (2)  | FCMP     |
| x > y       | FCOM                          | (U)COMISD (2)  | FCMP     |
| x == y      | FCOM                          | (U)COMISD (2)  | FCMP     |
| x < y       | FCOM                          | (U)COMISD (2)  | FCMP     |
| max(x,y)    | ?                             | MAXSD          | FMAX     | 
| min(x,y)    | ?                             | MINSD          | FMIN     | 
| x + y       | FADD                          | ADDSD          | FADD     |
| x - y       | FSUB                          | SUBSD          | FSUB     |
| x*y         | FMUL                          | MULSD          | FMUL     |
| x/y         | FDIV                          | DIVSD          | FDIV     |
| sqrt(x)     | FSQRT                         | SQRTSD         | FSQRT    |
| log2(x)     | FYL2X                         | /              | /        |
| exp2(x)     | F2XM1 + FADD + FSCALE         | /              | /        |
| x^y         | FYL2X + F2XM1 + FADD + FSCALE | /              | /        |
| sin(x)      | FSIN + ?                      | /              | /        |
| cos(x)      | FCOS + ?                      | /              | /        |

**NOTES**
- ***(1)*** These instructions don't have Scalar versions (only Packed versions)
- ***(2)*** Different comparison instructions in SSE2
     - CMPSD   : executes a specific comparison based on a 'predicate' (=instruction which comparison to perform) and outputs to a register all 0s or all 1s
     - COMISD  : executes comparison and sets flags (equal <=, >=, ...)   Assumes both are NaN (otherwise exception)
     - UCOMISD : same as COMISD but can handle NaNs according to some hardcoded rules (no exception)

(U)COMISD are most commonly used by current compilers like GCC.


## 4. References

The following data sources were used for analyzing the various CPUs.
(paths are relative to the `data` folder.)

| relevant data path | name                                                                               | author               | url                                                                                                                                                                                               | retrieved at |
|--------------------|------------------------------------------------------------------------------------|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|
| .                  | Simply FPU                                                                         | Raymond Filiatreault | https://masm32.com/masmcode/rayfil/tutorial/index.html                                                                                                                                            | 2025-09-13   |
| .                  | Intel 64-bit & IA-32 Architectures Software Developer's Manual (p451-...,p610-...) | Intel Corp.          | https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html                                                                                                               | 2025-09-20   |
| .                  | Arm A64 Instruction Set (p1066-...)                                                | Arm Ltd.             | https://developer.arm.com/Architectures/A-Profile%20Architecture#Downloads                                                                                                                        | 2025-09-20   |
| ./x86/             | Instruction Tables                                                                 | Agner Fog            | https://www.agner.org/optimize/instruction_tables.pdf                                                                                                                                             | 2025-09-13   |
| ./arm/             | Cortex A76 Software Optimization Guide                                             | Arm Ltd.             | https://developer.arm.com/documentation/PJDOC-466751330-7215/latest/                                                                                                                              | 2025-09-14   |
| ./arm/             | Cortex X1 Software Optimization Guide                                              | Arm Ltd.             | https://developer.arm.com/documentation/102174/latest/                                                                                                                                            | 2025-09-14   |
| ./arm/             | Cortex X2 Software Optimization Guide                                              | Arm Ltd.             | https://developer.arm.com/documentation/PJDOC-466751330-14955/latest/                                                                                                                             | 2025-09-14   |
| ./arm/             | Cortex X3 Software Optimization Guide                                              | Arm Ltd.             | https://developer.arm.com/documentation/PJDOC-466751330-590747/r1p2                                                                                                                               | 2025-09-14   |
| ./arm/             | Cortex X4 Software Optimization Guide                                              | Arm Ltd.             | https://developer.arm.com/documentation/PJDOC1505342170538636/latest/                                                                                                                             | 2025-09-27   |
| ./arm/             | Cortex X925 Software Optimization Guide                                            | Arm Ltd.             | https://developer.arm.com/documentation/109842/latest/                                                                                                                                            | 2025-09-27   |
| ./arm/             | Neoverse N1 Software Optimization Guide                                            | Arm Ltd.             | https://developer.arm.com/documentation/109896/0400/                                                                                                                                              | 2025-09-27   |
| ./arm/             | Neoverse N2 Software Optimization Guide                                            | Arm Ltd.             | https://developer.arm.com/documentation/109914/latest/                                                                                                                                            | 2025-09-27   |
| ./arm/             | Neoverse V1 Software Optimization Guide                                            | Arm Ltd.             | https://developer.arm.com/documentation/109897/0600/                                                                                                                                              | 2025-09-27   |
| ./arm/             | Neoverse V2 Software Optimization Guide                                            | Arm Ltd.             | https://developer.arm.com/documentation/109898/0300/                                                                                                                                              | 2025-09-27   |
| ./arm/             | Neoverse V3 Software Optimization Guide                                            | Arm Ltd.             | https://developer.arm.com/documentation/109678/300/                                                                                                                                               | 2025-09-27   |
| ./x86/amd/         | Software Optimization Guide for 19h family (Zen3)  (file 0 bytes !!!)              | AMD                  | https://docs.amd.com/v/u/en-US/56665                                                                                                                                                              | 2025-09-20   |
| ./x86/amd/         | Software Optimization Guide for the Zen4 Microarchitecture                         | AMD                  | https://docs.amd.com/v/u/en-US/57647_zen4_sog_1.01                                                                                                                                                | 2025-09-20   |
| ./x86/amd/         | Software Optimization Guide for the Zen5 Microarchitecture                         | AMD                  | https://docs.amd.com/v/u/en-US/58455_1.00                                                                                                                                                         | 2025-09-20   |
| ./x86/intel/       | Crestmont and Redwood Cove Microarchitecture Instruction Throughput and Latency    | Intel Corp.          | https://www.intel.com/content/www/us/en/content-details/825952/intel-processors-and-processor-cores-based-on-crestmont-and-redwood-cove-microarchitecture-instruction-throughput-and-latency.html | 2025-09-24   |
| ./x86/intel/       | Golden Cove Microarchitecture Instruction Throughput and Latency                   | Intel Corp.          | https://www.intel.com/content/www/us/en/content-details/723498/intel-processors-and-processor-cores-based-on-golden-cove-microarchitecture-instruction-throughput-and-latency.html                | 2025-09-24   |