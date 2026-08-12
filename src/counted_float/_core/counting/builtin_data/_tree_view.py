from __future__ import annotations

import math
from typing import TYPE_CHECKING

from counted_float._core.models import FlopType, FlopWeights

if TYPE_CHECKING:
    from ._dataset import NestedFlopWeights


class FlopWeightsTreeView:
    # -------------------------------------------------------------------------
    #  Constructor
    # -------------------------------------------------------------------------
    def __init__(self, name: str, children: FlopWeights | list[FlopWeightsTreeView]) -> None:
        # --- init ----------------------------------------
        self.lst_indent: list[int] = []
        self.lst_is_leaf: list[bool] = []
        self.lst_tree_str: list[str] = []
        self.lst_flop_weights: list[FlopWeights] = []

        # --- populate ------------------------------------
        if isinstance(children, FlopWeights):
            # this is a LEAF
            self.lst_indent = [0]
            self.lst_is_leaf = [True]
            self.lst_tree_str = [name]
            self.lst_flop_weights = [children]
        else:
            # this is a BRANCH

            # 1] root node
            self.lst_indent = [0]
            self.lst_is_leaf = [False]
            self.lst_tree_str = [name]
            self.lst_flop_weights = [
                FlopWeights.as_geo_mean(
                    [
                        child.lst_flop_weights[0]  # = avg of each sub-branch
                        for child in children
                    ]
                )
            ]

            # 2] child nodes
            for i_child, child in enumerate(children):
                for i_line, (indent, is_leaf, tree_str, flop_weights) in enumerate(
                    zip(
                        child.lst_indent,
                        child.lst_is_leaf,
                        child.lst_tree_str,
                        child.lst_flop_weights,
                        strict=True,
                    )
                ):
                    self.lst_indent.append(1 + indent)
                    self.lst_is_leaf.append(is_leaf)
                    #
                    if i_child < len(children) - 1:
                        if i_line == 0:
                            self.lst_tree_str.append(f" ├─{tree_str}")
                        else:
                            self.lst_tree_str.append(f" │ {tree_str}")
                    else:
                        if i_line == 0:
                            self.lst_tree_str.append(f" └─{tree_str}")
                        else:
                            self.lst_tree_str.append(f"   {tree_str}")
                    self.lst_flop_weights.append(flop_weights)

    # -------------------------------------------------------------------------
    #  Visualization
    # -------------------------------------------------------------------------
    def show(self) -> None:
        # rich is imported here rather than at module level: this module is reachable from the
        # counting path, while rendering a tree only ever happens on an explicit show()
        from rich.console import Console

        # --- prep ----------------------------------------
        console = Console()
        console_width = console.width
        tree_width = 5 + max([len(line) for line in self.lst_tree_str])
        sorted_flop_types = self.lst_flop_weights[0].get_sorted_flop_types()
        # right-aligned cells carry their own inter-column gap in the padding, so a column must be
        # at least one character wider than its header not to glue onto its left neighbor
        col_widths = {flop_type: max(10, len(flop_type.name) + 1) for flop_type in sorted_flop_types}

        # greedy packing: a block takes columns while their cumulative width fits the console
        # (every block gets at least one column, so a too-narrow console still renders)
        flop_types_per_block: list[list[FlopType]] = []
        block_width = 0
        for flop_type in sorted_flop_types:
            if not flop_types_per_block or block_width + col_widths[flop_type] > console_width - tree_width:
                flop_types_per_block.append([])
                block_width = 0
            flop_types_per_block[-1].append(flop_type)
            block_width += col_widths[flop_type]

        # --- show data -----------------------------------
        for flop_types in flop_types_per_block:
            # --- legend ---
            legend = " " * tree_width
            for flop_type in flop_types:
                legend += flop_type.name.rjust(col_widths[flop_type])
            console.print(legend, style="bold")

            # --- actual tree view ---
            for indent, is_leaf, tree_str, flop_weights in zip(
                self.lst_indent,
                self.lst_is_leaf,
                self.lst_tree_str,
                self.lst_flop_weights,
                strict=True,
            ):
                line = tree_str.ljust(tree_width)
                for flop_type in flop_types:
                    w = flop_weights.weights[flop_type]
                    if math.isnan(w):
                        line += "/ ".rjust(col_widths[flop_type])
                    elif isinstance(w, int):
                        line += str(w).rjust(col_widths[flop_type])
                    else:
                        line += f"{w:.2f}".rjust(col_widths[flop_type])

                if is_leaf:
                    # no special styling
                    console.print(line, highlight=False)
                else:
                    # highlight as bold and with a colored background.  The two bright bars pin a
                    # dark gray foreground instead of leaving it to the terminal default, which on
                    # dark themes is a light gray they leave barely legible (on the green one it
                    # all but disappears).  The darker bars keep the default, which reads fine on
                    # them either way.
                    style_tag = [
                        "[bold on #888888]",  # indent 0
                        "[bold on #7777dd]",  # indent 1
                        "[bold #333333 on #77dd77]",  # indent 2
                        "[bold #333333 on #ee7777]",  # indent 3
                        "[bold italic]",  # indent 4+
                    ][min(indent, 4)]
                    line = line[: 3 * indent] + style_tag + line[3 * indent :] + "[/]"
                    console.print(line, highlight=False)

            print()

    # -------------------------------------------------------------------------
    #  Factory methods
    # -------------------------------------------------------------------------
    @classmethod
    def from_nested_dict(cls, name: str, nested_dict: NestedFlopWeights) -> FlopWeightsTreeView:
        members = []
        for key in sorted(nested_dict.keys()):
            value = nested_dict[key]
            if isinstance(value, FlopWeights):
                members.append(FlopWeightsTreeView(name=key, children=value))
            else:
                members.append(FlopWeightsTreeView.from_nested_dict(name=key, nested_dict=value))

        return FlopWeightsTreeView(name=name, children=members)
