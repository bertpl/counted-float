"""Release driver for counted-float.

Run via ``make release VERSION=X.Y.Z``.  Validates state, gathers the badge
metrics, finalizes the changelog, commits, tags, opens a new Unreleased
section, commits, and pushes main + tag atomically.  The package version
itself is derived from the git tag at build time (hatch-vcs), so no version
bump is written.

Every check that can fail runs before the first write, so an abort always
leaves the tree as it was.  ``--dry-run`` stops at exactly that boundary.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
README = REPO_ROOT / "README.md"
PYTHON_VERSIONS_FILE = REPO_ROOT / ".python-versions"
SPLASH_SCRIPT = REPO_ROOT / ".github" / "scripts" / "create_splash.sh"
SPLASH_WEBP = REPO_ROOT / "images" / "splash_with_version.webp"
MUTATION_STATS_FILE = REPO_ROOT / "mutants" / "mutmut-cicd-stats.json"

PACKAGE_NAME = "counted-float"
CATEGORIES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# ceiling on the mutation measurement, past which the run is treated as unable to produce a number.
# A healthy full run finishes in a small fraction of this; the headroom is for a bad run, not for an
# unknown machine -- the release always runs on the maintainer's.
MUTATION_TIMEOUT_SEC = 600
# provenance line above the badge block: rewritten in place each release, never appended to
BADGE_STAMP_RE = re.compile(r"^<!-- badges below refreshed at release v[^>]*-->$", re.MULTILINE)


# ==================================================================================================
#  helpers
# ==================================================================================================
def run_command(cmd: list[str], **kw: object) -> str:
    """Run a subprocess and return stdout, or exit on failure."""
    # check=False is deliberate: the return code is handled below with
    # richer diagnostics than subprocess's own CalledProcessError.
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)
    if result.returncode != 0:
        sys.stderr.write(f"\n$ {' '.join(cmd)}\n")
        if result.stdout:
            sys.stderr.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.stdout


def print_step(n: int, msg: str) -> None:
    """Print a numbered step message."""
    print(f"  [{n:>2}] {msg}")


def fail_with_message(msg: str, code: int = 1) -> NoReturn:
    """Print an error and exit.

    ``NoReturn`` is the rarely-seen annotation for a function that never returns *at all* -- not one
    that returns ``None``. This one always leaves through ``sys.exit``, and saying so is what makes
    every guard clause below read correctly: ``if not m: fail_with_message(...)`` followed by
    ``m.group(1)`` is only sound because control cannot come back here.
    """
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse and validate a semver string."""
    if not SEMVER_RE.match(version):
        fail_with_message(f"VERSION {version!r} is not in X.Y.Z form")
    return tuple(int(p) for p in version.split("."))  # type: ignore[return-value]


def read_latest_tag_version() -> str:
    """Read the latest released version from the git tags reachable from HEAD."""
    tag = run_command(["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"]).strip()
    return tag.removeprefix("v")


def read_python_versions() -> list[str]:
    """Read supported Python versions from .python-versions."""
    return [v.strip() for v in PYTHON_VERSIONS_FILE.read_text().split() if v.strip()]


# ==================================================================================================
#  validation steps (1-7)
# ==================================================================================================
def step_1_check_working_tree() -> None:
    """Validate working tree is on main and clean."""
    print_step(1, "working tree on main and clean")
    branch = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip()
    if branch != "main":
        fail_with_message(f"not on main (currently on {branch})")
    porcelain = run_command(["git", "status", "--porcelain"])
    if porcelain.strip():
        fail_with_message("working tree has uncommitted changes:\n" + porcelain)


def step_2_check_in_sync() -> None:
    """Validate main is in sync with origin."""
    print_step(2, "main in sync with origin")
    run_command(["git", "fetch", "origin", "main"])
    local = run_command(["git", "rev-parse", "HEAD"]).strip()
    remote = run_command(["git", "rev-parse", "origin/main"]).strip()
    if local != remote:
        fail_with_message(f"local main ({local[:8]}) does not match origin/main ({remote[:8]})")


def step_3_check_version_upgrade(version: str) -> None:
    """Validate VERSION is strictly greater than the latest released tag."""
    print_step(3, f"VERSION {version} is an upgrade")
    new = parse_semver(version)
    current = parse_semver(read_latest_tag_version())
    if new <= current:
        fail_with_message(f"VERSION {version} is not greater than latest tag {'.'.join(str(p) for p in current)}")


def step_4_check_tag_doesnt_exist(version: str) -> None:
    """Validate tag does not exist locally or on origin."""
    print_step(4, f"tag v{version} does not exist (local + remote)")
    tag = f"v{version}"
    if run_command(["git", "tag", "-l", tag]).strip():
        fail_with_message(f"tag {tag} already exists locally")
    if run_command(["git", "ls-remote", "--tags", "origin", tag]).strip():
        fail_with_message(f"tag {tag} already exists on origin")


def step_5_check_pypi_doesnt_have(version: str) -> None:
    """Validate version is not already on PyPI."""
    print_step(5, f"version {version} is not on PyPI")
    url = f"https://pypi.org/pypi/{PACKAGE_NAME}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=10):
            fail_with_message(f"version {version} is already published on PyPI")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            fail_with_message(f"PyPI check returned HTTP {e.code}")


def step_6_check_classifiers_match() -> None:
    """Validate Python classifiers match .python-versions."""
    print_step(6, "Python classifiers in pyproject.toml match .python-versions")
    versions = read_python_versions()
    text = PYPROJECT.read_text()
    declared = set(re.findall(r'"Programming Language :: Python :: ([\d.]+)"', text))
    expected = set(versions)
    missing = expected - declared
    extra = declared - expected
    if missing or extra:
        fail_with_message(
            f"classifiers do not match .python-versions. "
            f"Missing: {sorted(missing) or 'none'}; "
            f"Extra: {sorted(extra) or 'none'}"
        )


def step_7_check_changelog_has_entries() -> None:
    """Validate Unreleased section has at least one bullet entry."""
    print_step(7, "CHANGELOG.md '## Unreleased' has at least one entry")
    text = CHANGELOG.read_text()
    m = re.search(r"^## Unreleased\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        fail_with_message("no '## Unreleased' section in CHANGELOG.md")
    if not re.search(r"^- ", m.group(1), re.MULTILINE):
        fail_with_message("'## Unreleased' has no bullet entries")


# ==================================================================================================
#  badge metrics (step 8)
# ==================================================================================================
# Gathering these is the last precondition, and the only one that can take minutes: it runs after
# every cheap check has passed and before the first write, so an abort here costs nothing to
# recover from.

# warn if the cumulative union exceeds this multiple of the largest single combo
TEST_COUNT_UNION_RATIO_WARN = 1.5


@dataclass(frozen=True)
class BadgeMetrics:
    """The badge numbers for one release, gathered before anything is written."""

    coverage_pct: float
    test_union: int
    mutation_pct: int


def _latest_main_coverage_run() -> tuple[str, str]:
    """Return (run_id, head_sha) of the latest successful 'Push to Main' run."""
    out = run_command(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            "push_to_main.yml",
            "--branch",
            "main",
            "--status",
            "success",
            "--limit",
            "1",
            "--json",
            "databaseId,headSha",
        ]
    )
    runs = json.loads(out)
    if not runs:
        fail_with_message("no successful 'Push to Main' run found to source coverage metrics from")
    return str(runs[0]["databaseId"]), runs[0]["headSha"]


def _fetch_release_metrics() -> dict[str, float]:
    """Download CI's cumulative metrics for the commit being released.

    The numbers come from the matrix combine job, not a local run, so the
    badge matches the CI gate exactly. Fails if the latest green main run is
    not the commit at HEAD (i.e. CI on current main hasn't gone green yet).
    """
    run_id, head_sha = _latest_main_coverage_run()
    local_head = run_command(["git", "rev-parse", "HEAD"]).strip()
    if head_sha != local_head:
        fail_with_message(
            f"latest main coverage run is for {head_sha[:8]}, not HEAD {local_head[:8]} — "
            "wait for CI on current main to go green before releasing"
        )
    with tempfile.TemporaryDirectory() as tmp:
        run_command(["gh", "run", "download", run_id, "--name", "release-metrics", "--dir", tmp])
        return json.loads((Path(tmp) / "metrics.json").read_text())


def _coverage_color(pct: float) -> str:
    """Map a coverage percentage to a shields.io badge color."""
    if pct >= 90:
        return "brightgreen"
    return "yellow" if pct >= 75 else "red"


def _mutation_color(pct: int) -> str:
    """Map a mutation score to a shields.io badge color.

    The thresholds sit lower than the coverage ones on purpose: a mutation score answers a
    stricter question -- would the suite *notice* this behavior change, not merely execute the
    line -- so a given percentage here is worth more than the same coverage percentage.
    """
    if pct >= 80:
        return "brightgreen"
    return "yellow" if pct >= 60 else "red"


def _measure_mutation_score() -> int:
    """Run the mutation suite locally and return its score as a whole percentage.

    Unlike the coverage and test-count metrics, this one cannot come from CI: mutation testing is
    deliberately kept off the pipeline (a full run takes minutes and gates nothing), so the release
    measures it here instead.

    Killed over *all* mutants: timeouts count toward the denominator but never the numerator, so a
    mutant that merely ran slowly is never scored as caught.

    Two questions are kept apart. Whether a number could be produced at all gates the release: a
    crashing suite, a missing or malformed stats file, an empty mutant set or a run past
    MUTATION_TIMEOUT_SEC all mean the measurement is broken, and swallowing that compounds
    silently across every later release -- the badge would keep claiming a figure nobody measured.
    What the number *is* never gates: the score wobbles run to run from timeout nondeterminism, so
    a threshold would reject releases over measurement noise.

    Returns:
        The rounded percentage.
    """
    print("  measuring the mutation score (runs the mutation suite; takes a few minutes)")
    MUTATION_STATS_FILE.unlink(missing_ok=True)
    for target in ("mutation", "mutation-stats"):
        # not run_command(): its diagnostics dump captured output, which for a full mutation run
        # buries the actual message -- the hint to re-run by hand is more useful here
        try:
            outcome = subprocess.run(
                ["make", target],
                cwd=REPO_ROOT,
                capture_output=True,
                check=False,
                timeout=MUTATION_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired:
            fail_with_message(
                f"'make {target}' did not finish within {MUTATION_TIMEOUT_SEC}s, so no mutation score "
                f"could be measured. Run it by hand to see where it hangs."
            )
        if outcome.returncode != 0:
            fail_with_message(
                f"'make {target}' failed, so no mutation score could be measured. "
                f"Run it by hand to see why -- its output is captured here to keep the release log readable."
            )
    try:
        stats = json.loads(MUTATION_STATS_FILE.read_text())
        killed, total = int(stats["killed"]), int(stats["total"])
    except (OSError, ValueError, KeyError) as exc:
        fail_with_message(f"could not read the mutation stats ({exc}), so no mutation score could be measured")
    if total <= 0:
        fail_with_message("the mutation run produced no mutants, so no mutation score could be measured")
    return round(100 * killed / total)


def step_8_gather_badge_metrics() -> BadgeMetrics:
    """Resolve every badge number, failing the release if any of them cannot be obtained."""
    print_step(8, "gather badge metrics (CI metrics for HEAD + local mutation score)")
    metrics = _fetch_release_metrics()
    union = int(metrics["test_union"])
    max_combo = int(metrics["test_max"])
    if max_combo and union > TEST_COUNT_UNION_RATIO_WARN * max_combo:
        print(
            f"\nWARNING: cumulative test count ({union}) exceeds "
            f"{TEST_COUNT_UNION_RATIO_WARN}x the largest single combo ({max_combo}). "
            "Node-id mismatches across combos can inflate the union — verify before publishing.\n",
            file=sys.stderr,
        )
    return BadgeMetrics(
        coverage_pct=float(metrics["coverage_pct"]),
        test_union=union,
        mutation_pct=_measure_mutation_score(),
    )


# ==================================================================================================
#  release commit steps (9-11)
# ==================================================================================================
def step_9_finalize_changelog(version: str) -> None:
    """Move Unreleased entries to a dated version section."""
    print_step(9, f"finalize CHANGELOG.md '## Unreleased' -> '## {version} ({date.today().isoformat()})'")
    text = CHANGELOG.read_text()
    m = re.search(r"^## Unreleased\s*$(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        fail_with_message("no '## Unreleased' section to finalize")
    body = m.group(1)
    new_body_lines: list[str] = []
    lines = body.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i]
        cat_match = re.match(r"^### (\w+)\s*$", line)
        if cat_match and cat_match.group(1) in CATEGORIES:
            j = i + 1
            has_entry = False
            while j < len(lines) and not re.match(r"^### ", lines[j]):
                if lines[j].lstrip().startswith("- "):
                    has_entry = True
                    break
                j += 1
            if has_entry:
                new_body_lines.append(line)
                i += 1
                while i < len(lines) and not re.match(r"^### ", lines[i]):
                    new_body_lines.append(lines[i])
                    i += 1
            else:
                i += 1
                while i < len(lines) and lines[i].strip() == "":
                    i += 1
        else:
            new_body_lines.append(line)
            i += 1
    new_body = "".join(new_body_lines).rstrip() + "\n"
    new_header = f"## {version} ({date.today().isoformat()})\n"
    text = text[: m.start()] + new_header + new_body + text[m.end() :]
    CHANGELOG.write_text(text)


def _stamp_badge_provenance(text: str, version: str) -> str:
    """Return the README text with its badge-provenance comment set to this release.

    The badge values are snapshots taken at release time, not live readings, so the comment
    records which release they describe. An HTML comment keeps it visible in the raw file and
    absent from the rendered page. Rewritten in place, so releases never stack up stamps.
    """
    stamp = f"<!-- badges below refreshed at release v{version} -->"
    if BADGE_STAMP_RE.search(text):
        return BADGE_STAMP_RE.sub(stamp, text, count=1)
    return f"{stamp}\n{text}"


def refresh_readme_badges(version: str, badges: BadgeMetrics) -> None:
    """Stamp the README badges from already-gathered numbers, and record the release they describe.

    Purely a write: everything that can fail was resolved during validation, so reaching here means
    the badge values are known and the provenance stamp cannot end up naming a release whose
    measurements were never taken.
    """
    text = README.read_text()
    text = re.sub(
        r"badge/coverage-[\d.]+%25-[a-z]+",
        f"badge/coverage-{badges.coverage_pct:.2f}%25-{_coverage_color(badges.coverage_pct)}",
        text,
    )
    text = re.sub(r"badge/tests-\d+-blue", f"badge/tests-{badges.test_union}-blue", text)
    text = re.sub(
        r"badge/mutmut-\d+%25-[a-z]+",
        f"badge/mutmut-{badges.mutation_pct}%25-{_mutation_color(badges.mutation_pct)}",
        text,
    )
    README.write_text(_stamp_badge_provenance(text, version))


def stamp_splash(version: str) -> None:
    """Stamp the release version onto the committed splash webp (needs ImageMagick).

    Runs create_splash.sh (the version overlay) on the committed, version-independent
    base image. Fails loudly if ``magick`` is absent, since a maintainer-driven release
    must produce the real asset.
    """
    if shutil.which("magick") is None:
        fail_with_message("ImageMagick ('magick') is required to stamp the release splash but was not found")
    run_command(["sh", str(SPLASH_SCRIPT), f"v{version}"], cwd=REPO_ROOT)


def step_10_commit_release(version: str, badges: BadgeMetrics) -> None:
    """Refresh README badges, stamp the splash, then create the release commit."""
    print_step(10, f"refresh README badges + stamp splash + commit 'release: {version}'")
    refresh_readme_badges(version, badges)
    stamp_splash(version)
    run_command(["git", "add", "CHANGELOG.md", "README.md", str(SPLASH_WEBP)])
    run_command(["git", "commit", "-m", f"release: {version}"])


def step_11_tag(version: str) -> None:
    """Create the version tag."""
    print_step(11, f"create tag v{version}")
    run_command(["git", "tag", f"v{version}"])


# ==================================================================================================
#  post-release steps (12-14)
# ==================================================================================================
def step_12_add_unreleased_section() -> None:
    """Add a fresh Unreleased section to the changelog."""
    print_step(12, "add fresh '## Unreleased' section to CHANGELOG.md")
    text = CHANGELOG.read_text()
    m = re.search(r"^## ", text, re.MULTILINE)
    if not m:
        fail_with_message("CHANGELOG.md has no version sections")
    insertion = "## Unreleased\n\n" + "\n".join(f"### {c}\n" for c in CATEGORIES) + "\n"
    text = text[: m.start()] + insertion + text[m.start() :]
    CHANGELOG.write_text(text)


def step_13_commit_next_cycle() -> None:
    """Commit the fresh Unreleased section."""
    print_step(13, "commit 'chore: begin next development cycle'")
    run_command(["git", "add", "CHANGELOG.md"])
    run_command(["git", "commit", "-m", "chore: begin next development cycle"])


def step_14_push(version: str) -> None:
    """Push main and the tag atomically."""
    print_step(14, f"push main + v{version} atomically")
    run_command(["git", "push", "--atomic", "origin", "main", f"refs/tags/v{version}"])


# ==================================================================================================
#  orchestration
# ==================================================================================================
def post_tag_recovery_hint(failed_step: int, version: str, also_next_cycle: bool) -> None:
    """Print recovery instructions after a post-tag failure."""
    reset_count = 2 if also_next_cycle else 1
    print(
        f"\nERROR: step {failed_step} failed.\n"
        f"Local state: release commit and tag v{version} created, not pushed.\n"
        f"To abort and retry:\n"
        f"  git tag -d v{version}\n"
        f"  git reset --hard HEAD~{reset_count}\n",
        file=sys.stderr,
    )


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="X.Y.Z (no leading v)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run every precondition, including the mutation measurement, then stop before the first write",
    )
    args = parser.parse_args()
    version = args.version
    parse_semver(version)

    print(f"Releasing {PACKAGE_NAME} v{version}\n")

    print("Validation:")
    step_1_check_working_tree()
    step_2_check_in_sync()
    step_3_check_version_upgrade(version)
    step_4_check_tag_doesnt_exist(version)
    step_5_check_pypi_doesnt_have(version)
    step_6_check_classifiers_match()
    step_7_check_changelog_has_entries()
    badges = step_8_gather_badge_metrics()

    if args.dry_run:
        print(
            f"\nDry run: every precondition passed and nothing was written.\n"
            f"  coverage {badges.coverage_pct:.2f}% | tests {badges.test_union} | mutation {badges.mutation_pct}%\n"
        )
        return

    print("\nRelease commit:")
    step_9_finalize_changelog(version)
    step_10_commit_release(version, badges)
    step_11_tag(version)

    print("\nPost-release:")
    also_next_cycle = False
    try:
        step_12_add_unreleased_section()
        step_13_commit_next_cycle()
        also_next_cycle = True
        step_14_push(version)
    except subprocess.CalledProcessError:
        post_tag_recovery_hint(12, version, also_next_cycle)
        sys.exit(1)
    except SystemExit:
        post_tag_recovery_hint(12, version, also_next_cycle)
        raise


if __name__ == "__main__":
    main()
