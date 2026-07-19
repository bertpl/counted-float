import math

from counted_float import CountedFloat, FlopCountingContext, Verbosity

cf = CountedFloat(1.73)

with FlopCountingContext(verbosity=Verbosity.INFO):
    _ = cf * cf
    _ = cf**2
    _ = math.log(cf, 2)
