# FLOP weights

## Weighted FLOP counting

The `counted_float` package contains a set of default, built-in FLOP weights,
based on both empirical measurements and theoretical estimates of the relative
cost of different floating point operations.

See [Methodology](analysis_methodology.md) for the rationale behind the choice
of data sources and methodology, and
[CPU architecture scope](cpu_architectures_scope.md) for the CPUs covered.

<!-- BEGIN generated: flop-weights-active -->
```python
>>> from counted_float.config import get_active_flop_weights

>>> get_active_flop_weights().show()

{
    FlopType.MINUS      [-x]            :   0.45000
    FlopType.ABS        [abs(x)]        :   0.70000
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.COMP       [x<=y]          :   1.00000
    FlopType.SUB        [x-y]           :   1.00000
    FlopType.COPYSIGN   [copysign(x,y)] :   1.20000
    FlopType.MUL        [x*y]           :   1.40000
    FlopType.FMA        [x*y+z]         :   1.80000
    FlopType.RND        [round]         :   1.80000
    FlopType.F2I        [float->int]    :   2.00000
    FlopType.I2F        [int->float]    :   2.00000
    FlopType.DIST_XARG  [dist(+arg)]    :   2.70000
    FlopType.HYPOT_XARG  [hypot(+arg)]  :   2.70000
    FlopType.DIV        [x/y]           :   5.50000
    FlopType.FMOD       [fmod(x,y)]     :   6.00000
    FlopType.SQRT       [sqrt(x)]       :   7.00000
    FlopType.REMAINDER  [remainder(x,y)]:  13.00000
    FlopType.EXP2       [2^x]           :  14.00000
    FlopType.EXP        [e^x]           :  16.00000
    FlopType.HYPOT      [hypot(x,y)]    :  18.00000
    FlopType.LOG        [log(x)]        :  18.00000
    FlopType.DIST       [dist(p,q)]     :  22.00000
    FlopType.EXP10      [10^x]          :  22.00000
    FlopType.LOG2       [log2(x)]       :  22.00000
    FlopType.COSH       [cosh(x)]       :  24.00000
    FlopType.ACOS       [acos(x)]       :  27.00000
    FlopType.ASIN       [asin(x)]       :  27.00000
    FlopType.ATAN       [atan(x)]       :  27.00000
    FlopType.LGAMMA     [lgamma(x)]     :  27.00000
    FlopType.LOG10      [log10(x)]      :  27.00000
    FlopType.COS        [cos(x)]        :  30.00000
    FlopType.LOG1P      [log1p(x)]      :  30.00000
    FlopType.SIN        [sin(x)]        :  30.00000
    FlopType.ACOSH      [acosh(x)]      :  36.00000
    FlopType.ASINH      [asinh(x)]      :  36.00000
    FlopType.ATAN2      [atan2(y,x)]    :  36.00000
    FlopType.CBRT       [cbrt(x)]       :  36.00000
    FlopType.EXPM1      [expm1(x)]      :  36.00000
    FlopType.ERFC       [erfc(x)]       :  40.00000
    FlopType.POW        [x^y]           :  40.00000
    FlopType.TAN        [tan(x)]        :  40.00000
    FlopType.ATANH      [atanh(x)]      :  45.00000
    FlopType.SINH       [sinh(x)]       :  45.00000
    FlopType.ERF        [erf(x)]        :  50.00000
    FlopType.TANH       [tanh(x)]       :  50.00000
    FlopType.GAMMA      [gamma(x)]      :  55.00000
    FlopType.SUMPROD    [sumprod(p,q)]  :       nan
    FlopType.SUMPROD_XELEM  [sumprod(+elem)]:       nan
}
```
<!-- END generated: flop-weights-active -->

Note that these weights are rounded up to the ~10% closest semi-round number,
reflecting a balance between accuracy and readability, while conveying the
message that these weights should be used as approximations only. See below
for the different rounding modes.

These weights will be used by default when extracting total weighted flop
costs:

```python
import math
from counted_float import CountedFloat, FlopCountingContext


cf1 = CountedFloat(1.73)
cf2 = CountedFloat(2.94)

with FlopCountingContext() as ctx:
    _ = cf1 + cf2
    _ = cf1 ** cf2
    _ = math.log2(cf2)

flop_counts = ctx.flop_counts()
total_cost = flop_counts.total_weighted_cost()  # 1 + 40 + 22 = 63
```

Note that the `total_weighted_cost` method will use the active flop weights
as returned by `get_active_flop_weights()`. This can be overridden by either
configuring different flop weights (see next section) or by setting the
`weights` argument of the `total_weighted_cost()` method.

## Configuring FLOP weights

We showed earlier that the `get_active_flop_weights()` function returns the
active FLOP weights. We can change these by using the
`set_active_flop_weights()` function, which takes a `FlopWeights` object as
an argument. This way we can configure
flop weights that might be obtained using benchmarks run on the target
hardware (see [Benchmarking](benchmarking.md)).

```python
from counted_float.config import set_active_flop_weights
from counted_float import FlopWeights

set_active_flop_weights(weights=FlopWeights(...))  # insert own weights here
```

## Inspecting built-in data

See [Built-in data](builtin_data.md) for what data ships with the package
and how the keys used for filtering below are structured.

### Default, pre-aggregated flop weights

Built-in flop weights can be inspected using the following functions:

<!-- BEGIN generated: flop-weights-consensus-raw -->
```python
from counted_float.config import get_default_consensus_flop_weights

>>> get_default_consensus_flop_weights(rounding_mode=None).show()

{
    FlopType.MINUS      [-x]            :   0.43808
    FlopType.ABS        [abs(x)]        :   0.70139
    FlopType.COMP       [x<=y]          :   0.97647
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00101
    FlopType.COPYSIGN   [copysign(x,y)] :   1.20668
    FlopType.MUL        [x*y]           :   1.40109
    FlopType.FMA        [x*y+z]         :   1.72446
    FlopType.RND        [round]         :   1.79790
    FlopType.F2I        [float->int]    :   1.92192
    FlopType.I2F        [int->float]    :   1.92910
    FlopType.HYPOT_XARG  [hypot(+arg)]  :   2.64488
    FlopType.DIST_XARG  [dist(+arg)]    :   2.68446
    FlopType.DIV        [x/y]           :   5.55314
    FlopType.FMOD       [fmod(x,y)]     :   6.12176
    FlopType.SQRT       [sqrt(x)]       :   7.10086
    FlopType.REMAINDER  [remainder(x,y)]:  13.31213
    FlopType.EXP2       [2^x]           :  13.71889
    FlopType.EXP        [e^x]           :  16.40822
    FlopType.LOG        [log(x)]        :  18.50176
    FlopType.HYPOT      [hypot(x,y)]    :  18.63083
    FlopType.EXP10      [10^x]          :  21.06590
    FlopType.LOG2       [log2(x)]       :  21.25532
    FlopType.DIST       [dist(p,q)]     :  22.52481
    FlopType.COSH       [cosh(x)]       :  23.82063
    FlopType.LOG10      [log10(x)]      :  25.52618
    FlopType.LGAMMA     [lgamma(x)]     :  26.28912
    FlopType.ACOS       [acos(x)]       :  27.13547
    FlopType.ATAN       [atan(x)]       :  27.69345
    FlopType.ASIN       [asin(x)]       :  27.88891
    FlopType.SIN        [sin(x)]        :  29.20149
    FlopType.LOG1P      [log1p(x)]      :  29.25856
    FlopType.COS        [cos(x)]        :  29.99393
    FlopType.ACOSH      [acosh(x)]      :  34.72153
    FlopType.ASINH      [asinh(x)]      :  36.31213
    FlopType.EXPM1      [expm1(x)]      :  36.72830
    FlopType.CBRT       [cbrt(x)]       :  36.95123
    FlopType.ATAN2      [atan2(y,x)]    :  37.56775
    FlopType.POW        [x^y]           :  39.36675
    FlopType.TAN        [tan(x)]        :  39.88646
    FlopType.ERFC       [erfc(x)]       :  40.43721
    FlopType.ATANH      [atanh(x)]      :  43.18809
    FlopType.SINH       [sinh(x)]       :  46.36347
    FlopType.TANH       [tanh(x)]       :  47.83127
    FlopType.ERF        [erf(x)]        :  48.01378
    FlopType.GAMMA      [gamma(x)]      :  56.40641
    FlopType.SUMPROD    [sumprod(p,q)]  :       nan
    FlopType.SUMPROD_XELEM  [sumprod(+elem)]:       nan
}
```
<!-- END generated: flop-weights-consensus-raw -->

There are 3 rounding modes:

- `None` -> no rounding
- `"nearest_int"` -> round up/down to nearest integer, with a minimum of 1
- `"10%"` -> round to nearest semi-round number within ~10% (default)

The default weights that are configured out-of-the-box in the package are the
`consensus` weights with the default `"10%"` rounding.

### Custom-aggregated flop weights

We can retrieve built-in flop weights in a more fine-grained manner, by custom
filtering and then aggregating them — by the same procedure used for the
default weights (see [How the final weights are
computed](#how-the-final-weights-are-computed) below), applied to the
filtered subset.

<!-- BEGIN generated: flop-weights-arm -->
```python
from counted_float.config import get_builtin_flop_weights

>>> get_builtin_flop_weights(key_filter="arm").show()

{
    FlopType.COMP       [x<=y]          :   0.65000
    FlopType.MINUS      [-x]            :   0.80000
    FlopType.ABS        [abs(x)]        :   1.00000
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00000
    FlopType.F2I        [float->int]    :   1.50000
    FlopType.MUL        [x*y]           :   1.50000
    FlopType.I2F        [int->float]    :   1.60000
    FlopType.RND        [round]         :   1.60000
    FlopType.COPYSIGN   [copysign(x,y)] :   1.80000
    FlopType.FMA        [x*y+z]         :   2.00000
    FlopType.DIST_XARG  [dist(+arg)]    :   3.30000
    FlopType.HYPOT_XARG  [hypot(+arg)]  :   3.30000
    FlopType.DIV        [x/y]           :   6.00000
    FlopType.FMOD       [fmod(x,y)]     :   7.50000
    FlopType.SQRT       [sqrt(x)]       :   7.50000
    FlopType.EXP2       [2^x]           :  15.00000
    FlopType.REMAINDER  [remainder(x,y)]:  15.00000
    FlopType.EXP        [e^x]           :  18.00000
    FlopType.LOG        [log(x)]        :  18.00000
    FlopType.HYPOT      [hypot(x,y)]    :  20.00000
    FlopType.LOG2       [log2(x)]       :  20.00000
    FlopType.EXP10      [10^x]          :  22.00000
    FlopType.DIST       [dist(p,q)]     :  24.00000
    FlopType.LOG10      [log10(x)]      :  24.00000
    FlopType.ACOS       [acos(x)]       :  27.00000
    FlopType.COSH       [cosh(x)]       :  27.00000
    FlopType.LGAMMA     [lgamma(x)]     :  27.00000
    FlopType.ASIN       [asin(x)]       :  30.00000
    FlopType.ATAN       [atan(x)]       :  30.00000
    FlopType.LOG1P      [log1p(x)]      :  30.00000
    FlopType.SIN        [sin(x)]        :  30.00000
    FlopType.COS        [cos(x)]        :  33.00000
    FlopType.ACOSH      [acosh(x)]      :  36.00000
    FlopType.ASINH      [asinh(x)]      :  36.00000
    FlopType.CBRT       [cbrt(x)]       :  36.00000
    FlopType.EXPM1      [expm1(x)]      :  36.00000
    FlopType.ATAN2      [atan2(y,x)]    :  40.00000
    FlopType.ERFC       [erfc(x)]       :  40.00000
    FlopType.POW        [x^y]           :  40.00000
    FlopType.TAN        [tan(x)]        :  40.00000
    FlopType.ATANH      [atanh(x)]      :  45.00000
    FlopType.SINH       [sinh(x)]       :  45.00000
    FlopType.TANH       [tanh(x)]       :  45.00000
    FlopType.ERF        [erf(x)]        :  50.00000
    FlopType.GAMMA      [gamma(x)]      :  60.00000
    FlopType.SUMPROD    [sumprod(p,q)]  :       nan
    FlopType.SUMPROD_XELEM  [sumprod(+elem)]:       nan
}
```
<!-- END generated: flop-weights-arm -->

## How the final weights are computed

The default weights and any filtered subset are produced by the very same
procedure — the default *is* the filtered subset with an empty filter, i.e.
`get_default_consensus_flop_weights()` is exactly
`get_builtin_flop_weights(key_filter="")`. So there is a single aggregation
mechanism behind every set of weights the package reports.

### Hierarchical aggregation

The matching data sources are not simply pooled into one flat average. They
are combined with the geometric mean **one level of the key hierarchy at a
time**, from the leaves up: individual sources are averaged within their
source type (`benchmarks`, `specs`, `other`), source types within their
µarch family, families within their ISA, and finally the two ISAs together.
The [built-in data reference](builtin_data.md) describes the hierarchy these
levels correspond to.

Aggregating level-by-level implicitly weights the *branches* of the tree
rather than the individual files, so a µarch family with many measured CPUs
does not drown out one with few, and the abundant benchmark results do not
overwhelm the sparser spec-sheet data. The geometric mean (rather than the
arithmetic mean) is used throughout because the weights are cost *ratios*:
it treats "twice as expensive" and "half as expensive" symmetrically.

### Imputation of missing weights

Not every data source covers every FLOP type: spec sheets and third-party
latency analyses only cover operations with hardware instructions, so their
entries have no weights for the transcendental functions (`sin`, `exp`,
`pow`, ...). Averaging such incomplete entries together with complete
benchmark results naively would bias the aggregate: whichever entries happen
to be complete would fully determine the expensive operations while also
pulling on the cheap ones.

Therefore, **at every level, missing values are imputed before that level's
geometric mean is taken.** The weights being combined form a matrix (FLOP
types x sources) which is approximated by a positive rank-1 factorization —
effectively "cost of the operation" x "speed of the source" — fitted to the
known values only; the missing cells are then filled from that
approximation. Intuitively: if a spec-sheet entry's known weights run ~20%
cheaper than its siblings', its missing transcendental weights are estimated
~20% cheaper than theirs too.

A value can only be imputed if its row and column each have at least one
known value; anything still missing afterwards stays missing in the
aggregate (shown as `/` in the `counted_float show-data` tree).
