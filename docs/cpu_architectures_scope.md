# CPU architecture scope

# 1. Introduction

As mentioned [here](./analysis_methodology.md), we will focus on the following classes of CPUs:

- x86 & arm  (dominant architectures in laptops, desktops & cloud computing)
- 64-bit architectures only
- CPUs released in the last 5-10yr, with higher emphasis on more recent models
- we focus on performance / balanced core microarchitectures, i.e. we explicitly do not consider efficiency cores

# 2. Scope of Architectures

## 2.1. x86

We can safely restrict ourselves to Intel & AMD processors, as these comprise the majority of x86 processors across
various segments.

## 2.1.1. Intel

- https://en.wikipedia.org/wiki/List_of_Intel_CPU_microarchitectures
- https://en.wikipedia.org/wiki/List_of_Intel_Core_processors

In general, we focus on those micro-architectures that are _not_ mobile-only and preferably are used in server processors.

| Released | Microarchitecture                                                                                                                                                            | Desktop / Mobile CPU                                                                                                                                                                     | Server CPU                                                                                      | Included? |
|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|-----------|
| 2017     | [Coffee Lake](https://en.wikipedia.org/wiki/Coffee_Lake)                                                                                                                     | Core i - 8th gen: [Coffee Lake](https://en.wikipedia.org/wiki/Coffee_Lake) <br> Core i - 9th gen: [Coffee Lake Refresh](https://en.wikipedia.org/wiki/Coffee_Lake)                       | /                                                                                               | V         |
| 2018     | [Palm Cove](https://en.wikipedia.org/wiki/Cannon_Lake_(microprocessor)#Design_history_and_features)                                                                          | Core Mobile i - 9th gen: [Cannon Lake](https://en.wikipedia.org/wiki/Cannon_Lake_(microprocessor))                                                                                       | /                                                                                               |           |
| 2019     | [Sunny Cove](https://en.wikipedia.org/wiki/Sunny_Cove_(microarchitecture)) <br> [Cypress Cove](https://en.wikipedia.org/wiki/Sunny_Cove_(microarchitecture)) (14nm backport) | Core Mobile i - 10th gen: [Ice Lake](https://en.wikipedia.org/wiki/Ice_Lake_(microprocessor)) <br> Core i - 11th gen: [Rocket Lake](https://en.wikipedia.org/wiki/Rocket_Lake)           | Xeon Scalable - 3rd gen: [Ice Lake-SP](https://en.wikipedia.org/wiki/Ice_Lake_(microprocessor)) | V         |
| 2020     | [Willow Cove](https://en.wikipedia.org/wiki/Willow_Cove) <br> (mostly a Sunny Cove process update)                                                                           | Core Mobile i - 11th gen: [Tiger Lake](https://en.wikipedia.org/wiki/Tiger_Lake)                                                                                                         | /                                                                                               |           |
| 2021     | [Golden Cove](https://en.wikipedia.org/wiki/Golden_Cove)                                                                                                                     | Core i - 12th gen: [Alder Lake](https://en.wikipedia.org/wiki/Alder_Lake) (P cores)                                                                                                      | Xeon Scalable - 4th gen: [Sapphire Rapids](https://en.wikipedia.org/wiki/Sapphire_Rapids)       | V         |
| 2022     | [Raptor Cove](https://en.wikipedia.org/wiki/Golden_Cove) <br> (~Golden Cove refresh)                                                                                         | Core i - 13th gen: [Raptor Lake](https://en.wikipedia.org/wiki/Raptor_Lake) (P cores) <br> Core i - 13th gen: [Raptor Lake Refresh](https://en.wikipedia.org/wiki/Raptor_Lake) (P cores) | Xeon Scalable - 5th gen: [Emerald Rapids](https://en.wikipedia.org/wiki/Emerald_Rapids)         | V         |
| 2023     | [Redwood Cove](https://chipsandcheese.com/p/intels-redwood-cove-baby-steps-are-still-steps) <br> (~Raptor Cove refresh) ***(1)***                                            | Core 1 Ultra: [Meteor Lake](https://en.wikipedia.org/wiki/Meteor_Lake) (P cores)                                                                                                         | Xeon 6: [Granite Rapids](https://en.wikipedia.org/wiki/Granite_Rapids)                          | V         |
| 2024     | [Lion Cove](https://en.wikipedia.org/wiki/Lion_Cove)                                                                                                                         | Core 2 Ultra: [Arrow Lake](https://en.wikipedia.org/wiki/Arrow_Lake_(microprocessor)) & [Lunar Lake](https://en.wikipedia.org/wiki/Lunar_Lake) (P cores)                                 | / ***(2)***                                                                                    |           |

**Notes:**

- ***(1)*** but with improvements to FPU multiplication latencies
- ***(2)*** no server variants announced at the time of writing.

## 2.1.2. AMD

- https://en.wikipedia.org/wiki/Zen_(microarchitecture)

- https://en.wikipedia.org/wiki/Epyc

| Released | Generation                                                                                                        | Desktop / Mobile CPU       | Server CPU          | Included ? |
|----------|-------------------------------------------------------------------------------------------------------------------|----------------------------|---------------------|------------|
| 2017     | [Zen 1](https://en.wikipedia.org/wiki/Zen_(first_generation)) <br> [Zen 1+](https://en.wikipedia.org/wiki/Zen%2B) | Ryzen 1000 <br> Ryzen 2000 | Epyc 7001           | V          |
| 2019     | [Zen 2](https://en.wikipedia.org/wiki/Zen_2)                                                                      | Ryzen 3000 <br> Ryzen 4000 | Epyc 7002           |            |
| 2020     | [Zen 3](https://en.wikipedia.org/wiki/Zen_3)                                                                      | Ryzen 5000 <br> Ryzen 6000 | Epyc 7003           | V          |
| 2022     | [Zen 4](https://en.wikipedia.org/wiki/Zen_4)                                                                      | Ryzen 7000 <br> Ryzen 8000 | Epyc 4004/8004/9004 | V          |
| 2024     | [Zen 5](https://en.wikipedia.org/wiki/Zen_5)                                                                     | Ryzen 9000                 | Epyc 4005/9005      | V          |

## 2.2. ARM

### 2.2.1. Approach

The ARM eco-system is a bit different, with not just the ISA being shared, but also ARM being a licenser of core designs,
that licensee can reuse as is, tweak to their specific needs or change heavily if so desired.

As such we will make an initial rough classification based on the version of the ARM ISA and potentially split up further
depending on available information, testable instances, etc...

Due to the aforementioned focus on 64-bit architectures, we will restrict this analysis to cores implementing the ARM v8
or higher and supporting a 64-bit mode (AARCH64 Execution State).Restricting ourselves further to architectures introduced
in the last ±10 years, we will focus on **ARM v8.2-A or higher**, as this ISA was introduced in 2016.

| Released  | ARMv8     | ARMv9               |
|-----------|-----------|---------------------|
| 2016-01   | ARMv8.2-A |                     |
| 2016-10   | ARMv8.3-A |                     |
| 2017-11   | ARMv8.4-A |                     |
| 2018-09   | ARMv8.5-A |                     |
| 2019-06   | ARMv8.6-A |                     |
| 2020-09   | ARMv8.7-A |                     |
| 2021-03   |           | ARMv9-A             |
| 2021-09   | ARMv8.8-A | ARMv9.3-A           |
| 2022-09   | ARMv8.9-A | ARMv9.4-A ***(1)*** |
| 2023-10   |           | ARMv9.5-A ***(1)*** |
| 2024-10   |           | ARMv9.6-A ***(1)*** |

Notes:

- ***(1)*** at the time of writing no chips have been released with support for these ISA levels.

Finally, since the ARM microarchitecture is used over a wide range of devices from low-power embedded chips to high-performance
HPC servers, we will restrict ourselves to ARM cores that are classified as either 'performance' or 'balanced', but will
consider **'efficiency' and similar** cores as **out-of-scope**.

More background:

- https://en.wikipedia.org/wiki/Comparison_of_ARM_processors
- https://en.wikipedia.org/wiki/AArch64

### 2.2.2. Overview of most common cores & chips

#### A. ARM core designs

| ARM Core Design                                                                     | ARM ISA level | Used in chips...                                             |
|-------------------------------------------------------------------------------------|---------------|--------------------------------------------------------------|
| [ARM Cortex A76](https://www.arm.com/products/silicon-ip-cpu/cortex-a/cortex-a76)   | V8.2-A        |                                                              |
| [ARM Cortex X1](https://en.wikipedia.org/wiki/ARM_Cortex-X1)                        | v8.2-A        |                                                              |
| [ARM Cortex X2](https://en.wikipedia.org/wiki/ARM_Cortex-X2)                        | v9.0-A        |                                                              |
| [ARM Cortex X3](https://en.wikipedia.org/wiki/ARM_Cortex-X3)                        | v9.0-A        |                                                              |
| [ARM Cortex X4](https://en.wikipedia.org/wiki/ARM_Cortex-X4)                        | v9.2-A        |                                                              |
| [ARM Cortex X925](https://en.wikipedia.org/wiki/ARM_Cortex-X925)                    | v9.2-A        |                                                              |
| [ARM Cortex C1-Ultra](https://www.arm.com/products/silicon-ip-cpu/c1-ultra)         | v9.3-A        |                                                              |
| [ARM Neoverse N1](https://www.arm.com/products/silicon-ip-cpu/neoverse/neoverse-n1) | v8.2-A        | [AWS Graviton 2](https://en.wikipedia.org/wiki/AWS_Graviton) |
| [ARM Neoverse N2](https://www.arm.com/products/silicon-ip-cpu/neoverse/neoverse-n2) | v9.0-A        | Azure Cobalt 100                                             |
| [ARM Neoverse V1](https://www.arm.com/products/silicon-ip-cpu/neoverse/neoverse-v1) | v8.4-A        | [AWS Graviton 3](https://en.wikipedia.org/wiki/AWS_Graviton) |
| [ARM Neoverse V2](https://www.arm.com/products/silicon-ip-cpu/neoverse/neoverse-v2) | v9.0-A        | [AWS Graviton 4](https://en.wikipedia.org/wiki/AWS_Graviton) |
| [ARM Neoverse V3](https://www.arm.com/products/silicon-ip-cpu/neoverse/neoverse-v3) | v9.2-A        |                                                              |

#### B. Other

| CPU                                                | ARM ISA level |
|----------------------------------------------------|---------------|
| [Apple M1](https://en.wikipedia.org/wiki/Apple_M1) | v8.4-A        |
| [Apple M2](https://en.wikipedia.org/wiki/Apple_M2) | v8.6-A        |
| [Apple M3](https://en.wikipedia.org/wiki/Apple_M3) | v8.6-A        |
| [Apple M4](https://en.wikipedia.org/wiki/Apple_M4) | v9.2-A        |

### 2.2.3. Selected cores & data sources

As indicated before, we'll make high-level split between the different ISA levels that are found in current & recent CPUs.
Note, that ISA level by itself does not necessarily impose latency specifications for certain instructions, but it can be used
as a proxy for the 'recency' & 'complexity' of a given chip.

| ARM ISA Level     | Data source               | Cores / Chips considered                                          |
|-------------------|---------------------------|-------------------------------------------------------------------|
| **V8.x** (>=v8.2) | → specs <br> → benchmarks | → A76, X1, N1, V1 <br> → Apple M1, Apple M3, AWS Graviton 2, AWS Graviton 3 |
| **V9.0**          | → specs <br> → benchmarks | → X2, X3, N2, V2 <br> → AWS Graviton 4, Azure Cobalt 100          |
| **V9.2**          | → specs <br> → benchmarks | → X4, X925, V3 <br> → Apple M4                                    |
