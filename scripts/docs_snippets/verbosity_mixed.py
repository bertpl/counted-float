import math

from counted_float import CountedFloat, FlopCountingContext, Verbosity

x = CountedFloat(0.6)

with FlopCountingContext(verbosity=Verbosity.INFO):
    _ = 1.0 - x * math.erf(x)
