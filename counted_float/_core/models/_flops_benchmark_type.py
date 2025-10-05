from enum import StrEnum


class FlopsBenchmarkType(StrEnum):
    # TODO: extend when we actually implement these benchmarks
    BASELINE = "baseline"
    ADD = "add"
    ADD_MINUS = "add_minus"
    ADD_ABS = "add_abs"
    ADD_ADD = "add_add"
    ADD_SUB = "add_sub"
    ADD_ROUND = "add_round"
    ADD_SQRT = "add_sqrt"
    ADD_LOG2 = "add_log2"
    ADD_LOG2_EXP2 = "add_log2_exp2"
    POW = "pow"
    POW_POW = "pow_pow"
    SUB = "sub"
    SUB_SUB = "sub_sub"
    MUL = "mul"
    MUL_MUL = "mul_mul"
    DIV = "div"
    DIV_DIV = "div_div"
    LTE_ADDSUB = "lte_addsub"
