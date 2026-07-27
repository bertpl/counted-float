"""Drop the click-based CLI tests from collection when the cli extra is not installed.

`test_cli.py` builds click invocations at module level, so the condition has to apply at collection
time rather than as a skip marker. `test_cli_main.py` stays: the entry point is installed
unconditionally, and most of what it asserts is what happens when the extra is absent.
"""

from counted_float._core.compatibility import Capability

collect_ignore = [] if Capability.CLI.is_available() else ["test_cli.py"]
