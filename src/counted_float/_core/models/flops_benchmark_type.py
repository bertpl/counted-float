from enum import StrEnum


class FlopsBenchmarkType(StrEnum):
    BASELINE = "baseline"
    ADD = "add"
    ADD_MINUS = "add_minus"
    ADD_ABS = "add_abs"
    ADD_COPYSIGN = "add_copysign"
    ADD_ADD = "add_add"
    ADD_SUB = "add_sub"
    ADD_ROUND = "add_round"
    ADD_SQRT = "add_sqrt"
    ADD_CBRT = "add_cbrt"
    ADD_LOG = "add_log"
    ADD_LOG_EXP = "add_log_exp"
    ADD_LOG2 = "add_log2"
    ADD_LOG2_EXP2 = "add_log2_exp2"
    ADD_LOG10 = "add_log10"
    ADD_LOG10_EXP10 = "add_log10_exp10"
    ADD_SIN = "add_sin"
    ADD_COS = "add_cos"
    ADD_TAN = "add_tan"
    ADD_SIN_ASIN = "add_sin_asin"
    ADD_SIN_ACOS = "add_sin_acos"
    ADD_ATAN = "add_atan"
    ADD_ATAN2 = "add_atan2"
    ADD_HYPOT = "add_hypot"
    # overflow-safe (scaled) hypot at two arities: their difference gives the per-extra-coordinate
    # slope (HYPOT_XARG); the 2-arg libm ADD_HYPOT above stays the HYPOT base weight (the scaled
    # arity-2 form reproduces it to within ~10%, so base and slope share one algorithm)
    ADD_HYPOT_SCALED2 = "add_hypot_scaled2"
    ADD_HYPOT_SCALED8 = "add_hypot_scaled8"
    # overflow-safe (scaled) Euclidean dist at two arities: DIST base weight from arity 2,
    # DIST_XARG slope from the pair
    ADD_DIST2 = "add_dist2"
    ADD_DIST8 = "add_dist8"
    # faithful ports of CPython's extended-precision sumprod loop (TripleLength accumulation,
    # error terms via hardware fma) at two arities: SUMPROD base weight (incl. the close-out)
    # from arity 2, SUMPROD_XELEM slope from the pair
    ADD_SUMPROD2 = "add_sumprod2"
    ADD_SUMPROD8 = "add_sumprod8"
    ADD_LOG1P = "add_log1p"
    ADD_LOG1P_EXPM1 = "add_log1p_expm1"
    ADD_FMOD = "add_fmod"
    ADD_REMAINDER = "add_remainder"
    ADD_TANH = "add_tanh"
    ADD_ASINH = "add_asinh"
    ADD_ASINH_SINH = "add_asinh_sinh"
    ADD_ACOSH = "add_acosh"
    ADD_ACOSH_COSH = "add_acosh_cosh"
    ADD_HALFSIN = "add_halfsin"
    ADD_HALFSIN_ATANH = "add_halfsin_atanh"
    # shared baseline for gamma/lgamma: 1.5 + 0.5*sin bounds the fed-back argument to [1, 2] near
    # gamma's minimum, so the chain can't run away into the OverflowError a naive f(tmp+x) chain hits
    ADD_GAMMABASE = "add_gammabase"
    ADD_GAMMABASE_GAMMA = "add_gammabase_gamma"
    ADD_GAMMABASE_LGAMMA = "add_gammabase_lgamma"
    ADD_ERF = "add_erf"
    ADD_ERFC = "add_erfc"
    POW = "pow"
    POW_POW = "pow_pow"
    SUB = "sub"
    SUB_SUB = "sub_sub"
    MUL = "mul"
    MUL_MUL = "mul_mul"
    DIV = "div"
    DIV_DIV = "div_div"
    FMA = "fma"
    FMA_FMA = "fma_fma"
    LTE_ADDSUB = "lte_addsub"
