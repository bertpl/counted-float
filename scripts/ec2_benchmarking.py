r"""Run the FLOPS benchmark on EC2 instances and collect the results.

For each target instance type this launches an ephemeral Amazon Linux 2023
instance, waits for its SSM agent, asserts the CPU is the exact
microarchitecture the target claims (so a mislabelled instance can never
contribute data), runs ``counted_float benchmark`` on it via SSM Run Command,
pulls the result JSON back over the command output, and terminates the
instance. No S3 and no inbound network are involved; the JSON (~6 KB) fits in
the SSM command output.

All account-specific values are arguments -- nothing here is repo-specific.

Prerequisites: an active SSO session (``aws sso login --profile <profile>``)
and the AWS CLI on PATH.

Usage:
    uv run python scripts/ec2_benchmarking.py \\
        --profile <sso-profile> --region eu-central-1 \\
        --instance-profile counted-float-benchmarking \\
        --subnet-id <subnet-id> --security-group-id <security-group-id>

Results are written as ``<instance_type>.json`` under ``--output-dir`` for
inspection; this script commits nothing.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Public SSM parameter holding the latest AL2023 AMI id, per architecture.
AL2023_AMI_PARAMETER = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-{arch}"


def benchmark_script(package_spec: str, python_version: str) -> str:
    """Remote shell: install uv, run the benchmark from `package_spec`, emit only the JSON.

    Installs git so a ``git+`` `package_spec` (an unreleased ref, as the data
    refresh needs) can be built. Pins the interpreter with ``uvx --python`` so
    uv downloads a managed CPython rather than falling back to AL2023's system
    Python 3.9 (which is below the package's floor); the version is also
    recorded in the result for provenance. `HOME` is unset in the SSM (root)
    execution environment, so it is defaulted explicitly -- `set -u` would
    otherwise abort on the `$HOME` reference. Every setup command keeps stdout
    off (its stderr is preserved) so the command output is exactly the JSON.
    """
    return (
        "set -euo pipefail\n"
        'export HOME="${HOME:-/root}"\n'
        "dnf install -y git >/dev/null\n"
        "curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1\n"
        'export PATH="$HOME/.local/bin:$PATH"\n'
        # stdout (the human-readable table) is dropped so the command output is
        # exactly the JSON; stderr is kept so a failure surfaces in SSM's error content.
        f"uvx --python {shlex.quote(python_version)} --from {shlex.quote(package_spec)} "
        "counted_float benchmark --output /tmp/result.json >/dev/null\n"
        "cat /tmp/result.json\n"
    )


# awk commands emitting a `k=v;k=v` CPU-identity line parsed by parse_cpu_id(). The
# `$1 ~ /^model[[:space:]]*$/` guard matches the `model` line without also
# matching `model name`.
CPU_ID_COMMANDS = {
    "x86_64": (
        "awk -F: '"
        "$1 ~ /^vendor_id[[:space:]]*$/{v=$2} "
        "$1 ~ /^cpu family[[:space:]]*$/{f=$2} "
        "$1 ~ /^model[[:space:]]*$/{m=$2} "
        'END{gsub(/[[:space:]]/,"",v);gsub(/[[:space:]]/,"",f);gsub(/[[:space:]]/,"",m);'
        'print "vendor="v";family="f";model="m}\' /proc/cpuinfo'
    ),
    "arm64": (
        "awk -F: '"
        "$1 ~ /^CPU implementer[[:space:]]*$/{i=$2} "
        "$1 ~ /^CPU part[[:space:]]*$/{p=$2} "
        'END{gsub(/[[:space:]]/,"",i);gsub(/[[:space:]]/,"",p);'
        'print "part="p";implementer="i}\' /proc/cpuinfo'
    ),
}


# ==================================================================================================
#  Targets
# ==================================================================================================
@dataclass(frozen=True)
class TargetInstance:
    """An EC2 instance type paired with the CPU identity it must have to be benchmarked."""

    instance_type: str
    arch: str  # "arm64" | "x86_64" -- selects the AL2023 AMI and the CPU-identity command
    expected: dict[
        str, str
    ]  # identity fields the CPU-identity command must return (x86: vendor/family/model; arm: part)


# Each target is sized to two physical cores: the benchmark is single-core, so
# the second core absorbs OS / SSM-agent / JIT background work without
# preempting the measured thread, and a uniform core count keeps runs
# comparable. Two vCPU sizes map to that, by threading model:
#   .large  (2 vCPU) -- Graviton (1 thread/core) and zen4/zen5 (SMT-off here)
#   .xlarge (4 vCPU) -- SMT-2 cores (Intel server + zen1/zen3), 2 vCPU/core
# Every launch is gated on the identity below, asserted against the reported
# CPUID/MIDR before benchmarking, so a re-backed family can't mislabel data.
# MIDR part id -> Neoverse core name. py-cpuinfo cannot resolve these newer ARM parts to a
# brand string, so Graviton results come back with a blank `description`; the backfill in
# benchmark_one fills it from the part the identity gate has already verified against the
# live CPU. This is the single source of truth for the arm part ids used by the gate below.
NEOVERSE_CORES: dict[str, str] = {
    "0xd0c": "Neoverse-N1",  # Graviton 2
    "0xd40": "Neoverse-V1",  # Graviton 3
    "0xd4f": "Neoverse-V2",  # Graviton 4
    "0xd84": "Neoverse-V3",  # Graviton 5
}

TARGETS: dict[str, TargetInstance] = {
    # Graviton, 1 thread/core -> .large = 2 physical cores
    "m6g.large": TargetInstance("m6g.large", "arm64", {"part": "0xd0c"}),  # Graviton 2 / Neoverse N1
    "m7g.large": TargetInstance("m7g.large", "arm64", {"part": "0xd40"}),  # Graviton 3 / Neoverse V1
    "m8g.large": TargetInstance("m8g.large", "arm64", {"part": "0xd4f"}),  # Graviton 4 / Neoverse V2
    "m9g.large": TargetInstance("m9g.large", "arm64", {"part": "0xd84"}),  # Graviton 5 / Neoverse V3
    # AMD Genoa/Turin, SMT-off -> .large = 2 physical cores (Turin: family alone pins zen5)
    "m7a.large": TargetInstance("m7a.large", "x86_64", {"vendor": "AuthenticAMD", "family": "25", "model": "17"}),
    "m8a.large": TargetInstance("m8a.large", "x86_64", {"vendor": "AuthenticAMD", "family": "26"}),
    # Intel server, SMT-2 -> .xlarge = 2 physical cores (Ice Lake-SP/Sapphire/Emerald/Granite Rapids)
    "m6i.xlarge": TargetInstance("m6i.xlarge", "x86_64", {"vendor": "GenuineIntel", "family": "6", "model": "106"}),
    "m7i.xlarge": TargetInstance("m7i.xlarge", "x86_64", {"vendor": "GenuineIntel", "family": "6", "model": "143"}),
    "i7i.xlarge": TargetInstance("i7i.xlarge", "x86_64", {"vendor": "GenuineIntel", "family": "6", "model": "207"}),
    "m8i.xlarge": TargetInstance("m8i.xlarge", "x86_64", {"vendor": "GenuineIntel", "family": "6", "model": "173"}),
    # AMD Milan/Naples, SMT-2 -> .xlarge = 2 physical cores
    "m6a.xlarge": TargetInstance("m6a.xlarge", "x86_64", {"vendor": "AuthenticAMD", "family": "25", "model": "1"}),
    "m5a.xlarge": TargetInstance("m5a.xlarge", "x86_64", {"vendor": "AuthenticAMD", "family": "23", "model": "1"}),
}


# ==================================================================================================
#  Config
# ==================================================================================================
@dataclass(frozen=True)
class Config:
    """Runtime configuration: AWS coordinates, network placement, and timeouts."""

    profile: str
    region: str
    instance_profile: str
    subnet_id: str
    security_group_id: str
    output_dir: Path
    package_spec: str = "counted-float[numba,cli]"
    python_version: str = "3.13"
    keep: bool = False
    ssm_ready_timeout: int = 240  # seconds to wait for the SSM agent to register
    command_timeout: int = 600  # seconds to wait for a single SSM command

    @property
    def aws_base(self) -> list[str]:
        """Base AWS CLI invocation with profile, region, and JSON output."""
        return ["aws", "--profile", self.profile, "--region", self.region, "--output", "json"]


# ==================================================================================================
#  AWS CLI wrappers
# ==================================================================================================
def aws_json(cfg: Config, *args: str) -> object:
    """Run an AWS CLI command and return its parsed JSON output."""
    out = _run(cfg.aws_base + list(args))
    return json.loads(out) if out.strip() else None


def latest_al2023_ami(cfg: Config, arch: str) -> str:
    """Resolve the newest AL2023 AMI id for the given architecture via the public SSM parameter."""
    value = aws_json(
        cfg,
        "ssm",
        "get-parameter",
        "--name",
        AL2023_AMI_PARAMETER.format(arch=arch),
        "--query",
        "Parameter.Value",
    )
    if not isinstance(value, str):
        raise RuntimeError(f"could not resolve AL2023 AMI for arch '{arch}'")
    return value


def run_instance(cfg: Config, target: TargetInstance, ami: str) -> str:
    """Launch one tagged instance and return its instance id.

    Sets shutdown-behavior to terminate as a backstop, so the instance cannot
    survive as a cost leak even if this script dies before the explicit
    terminate.
    """
    tags = "ResourceType=instance,Tags=[{Key=Project,Value=counted-float},{Key=Purpose,Value=benchmarking}]"
    result = aws_json(
        cfg,
        "ec2",
        "run-instances",
        "--image-id",
        ami,
        "--instance-type",
        target.instance_type,
        "--iam-instance-profile",
        f"Name={cfg.instance_profile}",
        "--subnet-id",
        cfg.subnet_id,
        "--security-group-ids",
        cfg.security_group_id,
        "--count",
        "1",
        "--instance-initiated-shutdown-behavior",
        "terminate",
        "--tag-specifications",
        tags,
        "--query",
        "Instances[0].InstanceId",
    )
    if not isinstance(result, str):
        raise RuntimeError(f"run-instances did not return an instance id for {target.instance_type}")
    return result


def terminate_instance(cfg: Config, instance_id: str) -> None:
    """Terminate an instance, swallowing errors so cleanup never masks the real failure."""
    try:
        aws_json(cfg, "ec2", "terminate-instances", "--instance-ids", instance_id, "--query", "TerminatingInstances")
    except subprocess.CalledProcessError:
        print(f"      WARNING: failed to terminate {instance_id}; terminate it manually", file=sys.stderr)


def wait_ssm_online(cfg: Config, instance_id: str) -> None:
    """Block until the instance's SSM agent reports Online, or raise on timeout."""
    deadline = time.monotonic() + cfg.ssm_ready_timeout
    while time.monotonic() < deadline:
        info = aws_json(
            cfg,
            "ssm",
            "describe-instance-information",
            "--filters",
            f"Key=InstanceIds,Values={instance_id}",
            "--query",
            "InstanceInformationList[0].PingStatus",
        )
        if info == "Online":
            return
        time.sleep(5)
    raise RuntimeError(f"instance {instance_id} did not become SSM-Online within {cfg.ssm_ready_timeout}s")


def run_ssm_command(cfg: Config, instance_id: str, script: str) -> str:
    """Send a shell script via SSM Run Command, wait for it, and return its stdout.

    Raises:
        RuntimeError: If the command does not finish Success within the
            timeout; the message carries the remote stderr for diagnosis.
    """
    sent = aws_json(
        cfg,
        "ssm",
        "send-command",
        "--instance-ids",
        instance_id,
        "--document-name",
        "AWS-RunShellScript",
        "--parameters",
        json.dumps({"commands": [script]}),
        "--query",
        "Command.CommandId",
    )
    if not isinstance(sent, str):
        raise RuntimeError("send-command did not return a command id")

    deadline = time.monotonic() + cfg.command_timeout
    while time.monotonic() < deadline:
        time.sleep(5)
        # get-command-invocation briefly 404s right after send; treat that as "still pending".
        try:
            inv = aws_json(
                cfg,
                "ssm",
                "get-command-invocation",
                "--command-id",
                sent,
                "--instance-id",
                instance_id,
            )
        except subprocess.CalledProcessError:
            continue
        if not isinstance(inv, dict):
            continue
        status = inv.get("Status")
        if status == "Success":
            return str(inv.get("StandardOutputContent", ""))
        if status in {"Failed", "Cancelled", "TimedOut"}:
            stderr = str(inv.get("StandardErrorContent", "")).strip()
            raise RuntimeError(f"SSM command {status} on {instance_id}: {stderr}")
    raise RuntimeError(f"SSM command did not finish within {cfg.command_timeout}s on {instance_id}")


# ==================================================================================================
#  CPU identity gate
# ==================================================================================================
def parse_cpu_id(output: str) -> dict[str, str]:
    """Parse a `k=v;k=v` CPU-identity line into a dict."""
    fields: dict[str, str] = {}
    for pair in output.strip().split(";"):
        if "=" in pair:
            key, _, value = pair.partition("=")
            fields[key.strip()] = value.strip()
    return fields


def assert_cpu_identity(target: TargetInstance, cpu_id_output: str) -> dict[str, str]:
    """Assert the reported CPU identity matches every expected field, or raise.

    Returns:
        The parsed identity fields, for logging.

    Raises:
        RuntimeError: On any mismatch or missing field -- the gate that keeps a
            mislabelled instance from producing data.
    """
    actual = parse_cpu_id(cpu_id_output)
    mismatches = [
        f"{key}: expected {value!r}, got {actual.get(key)!r}"
        for key, value in target.expected.items()
        if actual.get(key) != value
    ]
    if mismatches:
        raise RuntimeError(f"CPU identity mismatch for {target.instance_type}: " + "; ".join(mismatches))
    return actual


# ==================================================================================================
#  Orchestration
# ==================================================================================================
@dataclass
class RunResult:
    """Outcome of benchmarking one target."""

    instance_type: str
    ok: bool
    detail: str
    result_path: Path | None = None


def backfill_arm_core_description(data: dict, identity: dict[str, str]) -> None:
    """Fill a blank processor description from the gate-verified MIDR part, in place.

    py-cpuinfo does not resolve the newer Neoverse parts to a brand string, so Graviton
    results arrive with an empty `description`. The identity gate has already asserted the
    MIDR part against the live CPU, so the mapped core name is authoritative. Only fills a
    genuinely blank description; x86 identities carry no `part`, so they are left untouched.
    """
    processor = data.get("system", {}).get("processor", {})
    if not processor.get("description"):
        core = NEOVERSE_CORES.get(identity.get("part", ""))
        if core:
            processor["description"] = core


def benchmark_one(cfg: Config, target: TargetInstance) -> RunResult:
    """Launch, gate, benchmark, collect, and terminate one target instance."""
    instance_id: str | None = None
    try:
        ami = latest_al2023_ami(cfg, target.arch)
        print(f"      launching {target.instance_type} ({target.arch}, ami {ami})")
        instance_id = run_instance(cfg, target, ami)
        print(f"      instance {instance_id} -- waiting for SSM")
        wait_ssm_online(cfg, instance_id)

        cpu_id_line = run_ssm_command(cfg, instance_id, CPU_ID_COMMANDS[target.arch])
        identity = assert_cpu_identity(target, cpu_id_line)
        print(f"      CPU identity OK: {identity}")

        print("      running benchmark (install + JIT + measure ~5 min)")
        result_json = run_ssm_command(cfg, instance_id, benchmark_script(cfg.package_spec, cfg.python_version))
        data = json.loads(result_json)  # validates it parsed; also fails loudly on truncation
        backfill_arm_core_description(data, identity)  # name the Neoverse core py-cpuinfo left blank

        result_path = cfg.output_dir / f"{target.instance_type}.json"
        result_path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
        return RunResult(target.instance_type, ok=True, detail="benchmarked", result_path=result_path)
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return RunResult(target.instance_type, ok=False, detail=str(exc))
    finally:
        if instance_id and not cfg.keep:
            print(f"      terminating {instance_id}")
            terminate_instance(cfg, instance_id)


# ==================================================================================================
#  Helpers / CLI
# ==================================================================================================
def _run(cmd: list[str]) -> str:
    """Run a subprocess, returning stdout or raising with the captured output on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(f"\n$ {' '.join(cmd)}\n{result.stdout}{result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.stdout


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", required=True, help="AWS SSO profile (must have an active `aws sso login`)")
    parser.add_argument("--region", required=True, help="AWS region, e.g. eu-central-1")
    parser.add_argument("--instance-profile", required=True, help="IAM instance profile granting SSM access")
    parser.add_argument("--subnet-id", required=True, help="Subnet with outbound internet + SSM reachability")
    parser.add_argument("--security-group-id", required=True, help="Egress-only security group")
    parser.add_argument(
        "--instances",
        nargs="+",
        choices=sorted(TARGETS),
        default=sorted(TARGETS),
        help="Subset of target instance types (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/counted-float-benchmarking"),
        help="Directory for the collected result JSON files",
    )
    parser.add_argument(
        "--package-spec",
        default="counted-float[numba,cli]",
        help=(
            "uvx --from spec for the package to benchmark (default: the released PyPI package); "
            "pass e.g. 'counted-float[numba,cli] @ git+https://github.com/bertpl/counted-float@main' "
            "to benchmark an unreleased ref"
        ),
    )
    parser.add_argument(
        "--python-version",
        default="3.13",
        help="Python version uvx runs the benchmark under (uv downloads it if absent)",
    )
    parser.add_argument("--keep", action="store_true", help="Do not terminate instances (debugging)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Benchmark every selected target and report a summary; return non-zero if any failed."""
    args = parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cfg = Config(
        profile=args.profile,
        region=args.region,
        instance_profile=args.instance_profile,
        subnet_id=args.subnet_id,
        security_group_id=args.security_group_id,
        output_dir=args.output_dir,
        package_spec=args.package_spec,
        python_version=args.python_version,
        keep=args.keep,
    )

    results: list[RunResult] = []
    for name in args.instances:
        print(f"\n=== {name} ===")
        results.append(benchmark_one(cfg, TARGETS[name]))

    print("\n=== summary ===")
    for r in results:
        status = "OK  " if r.ok else "FAIL"
        location = f" -> {r.result_path}" if r.result_path else ""
        print(f"  [{status}] {r.instance_type}: {r.detail}{location}")

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
