# FLOP weights

## Weighted FLOP counting

The `counted_float` package contains a set of default, built-in FLOP weights,
based on both empirical measurements and theoretical estimates of the relative
cost of different floating point operations.

See [Methodology](analysis_methodology.md) for the rationale behind the choice
of data sources and methodology, and
[CPU architecture scope](cpu_architectures_scope.md) for the CPUs covered.

```
>>> from counted_float.config import get_active_flop_weights
>>> get_active_flop_weights().show()

{
    FlopType.MINUS      [-x]            :   0.45000
    FlopType.ABS        [abs(x)]        :   0.70000
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.COMP       [x<=y]          :   1.00000
    FlopType.SUB        [x-y]           :   1.00000
    FlopType.MUL        [x*y]           :   1.40000
    FlopType.RND        [round]         :   1.80000
    FlopType.F2I        [float->int]    :   2.00000
    FlopType.I2F        [int->float]    :   2.00000
    FlopType.DIV        [x/y]           :   5.50000
    FlopType.SQRT       [sqrt(x)]       :   7.50000
    FlopType.EXP2       [2^x]           :  16.00000
    FlopType.EXP        [e^x]           :  18.00000
    FlopType.LOG        [log(x)]        :  18.00000
    FlopType.EXP10      [10^x]          :  22.00000
    FlopType.LOG2       [log2(x)]       :  22.00000
    FlopType.LOG10      [log10(x)]      :  24.00000
    FlopType.COS        [cos(x)]        :  30.00000
    FlopType.SIN        [sin(x)]        :  30.00000
    FlopType.POW        [x^y]           :  40.00000
    FlopType.TAN        [tan(x)]        :  40.00000
    FlopType.CBRT       [cbrt(x)]       :  45.00000
}
```

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

Note that the `total_weighted_cost` method will use the default flop weights
as returned by `get_flop_weights()`. This can be overridden by either
configuring different flop weights (see next section) or by setting the
`weights` argument of the `total_weighted_cost()` method.

## Configuring FLOP weights

We showed earlier that the `get_flop_weights()` function returns the default
FLOP weights. We can change this by using the `set_flop_weights()` function,
which takes a `FlopWeights` object as an argument. This way we can configure
flop weights that might be obtained using benchmarks run on the target
hardware (see [Benchmarking](benchmarking.md)).

```python
from counted_float.config import set_active_flop_weights
from counted_float import FlopWeights

set_active_flop_weights(weights=FlopWeights(...))  # insert own weights here
```

## Inspecting built-in data

### Default, pre-aggregated flop weights

Built-in flop weights can be inspected using the following functions:

```python
from counted_float.config import get_default_consensus_flop_weights

>>> get_default_consensus_flop_weights(rounding_mode=None).show()

{
    FlopType.MINUS      [-x]            :   0.43688
    FlopType.ABS        [abs(x)]        :   0.71585
    FlopType.COMP       [x<=y]          :   0.97866
    FlopType.SUB        [x-y]           :   0.99565
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.MUL        [x*y]           :   1.39506
    FlopType.RND        [round]         :   1.78130
    FlopType.F2I        [float->int]    :   1.91125
    FlopType.I2F        [int->float]    :   1.91839
    FlopType.DIV        [x/y]           :   5.53385
    FlopType.SQRT       [sqrt(x)]       :   7.37309
    FlopType.EXP2       [2^x]           :  15.79616
    FlopType.EXP        [e^x]           :  17.45201
    FlopType.LOG        [log(x)]        :  18.93143
    FlopType.LOG2       [log2(x)]       :  22.29433
    FlopType.EXP10      [10^x]          :  22.93876
    FlopType.LOG10      [log10(x)]      :  24.56277
    FlopType.SIN        [sin(x)]        :  30.28970
    FlopType.COS        [cos(x)]        :  31.27413
    FlopType.POW        [x^y]           :  41.65022
    FlopType.TAN        [tan(x)]        :  41.99495
    FlopType.CBRT       [cbrt(x)]       :  44.15405
}
```

There are 3 rounding modes:

- `None` -> no rounding
- `"nearest_int"` -> round up/down to nearest integer, with a minimum of 1
- `"10%"` -> round to nearest semi-round number within ~10% (default)

The default weights that are configured out-of-the-box in the package are the
integer-rounded `consensus` weights.

### Custom-aggregated flop weights

We can retrieve built-in flop weights in a more fine-grained manner, by custom
filtering and then aggregating them with the geometric mean.

```python
from counted_float.config import get_builtin_flop_weights

>>> get_builtin_flop_weights(key_filter="arm").show()

{
    FlopType.COMP       [x<=y]          :   0.65000
    FlopType.MINUS      [-x]            :   0.90000
    FlopType.ADD        [x+y]           :   1.00000
    FlopType.SUB        [x-y]           :   1.00000
    FlopType.ABS        [abs(x)]        :   1.10000
    FlopType.F2I        [float->int]    :   1.50000
    FlopType.MUL        [x*y]           :   1.50000
    FlopType.I2F        [int->float]    :   1.60000
    FlopType.RND        [round]         :   1.60000
    FlopType.DIV        [x/y]           :   6.00000
    FlopType.SQRT       [sqrt(x)]       :   7.50000
    FlopType.EXP2       [2^x]           :  16.00000
    FlopType.EXP        [e^x]           :  18.00000
    FlopType.LOG        [log(x)]        :  20.00000
    FlopType.LOG2       [log2(x)]       :  20.00000
    FlopType.EXP10      [10^x]          :  24.00000
    FlopType.LOG10      [log10(x)]      :  24.00000
    FlopType.COS        [cos(x)]        :  33.00000
    FlopType.SIN        [sin(x)]        :  33.00000
    FlopType.POW        [x^y]           :  40.00000
    FlopType.CBRT       [cbrt(x)]       :  45.00000
    FlopType.TAN        [tan(x)]        :  45.00000
}
```
