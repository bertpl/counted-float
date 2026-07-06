"""MkDocs hook that injects the repo-root CHANGELOG.md into the site as changelog.md.

Wired up via `hooks:` in mkdocs.yml — a plain hook keeps the docs build free of
third-party plugins for what is a single-file copy.
"""

from pathlib import Path

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File, Files


def on_files(files: Files, config: MkDocsConfig) -> Files:
    """Add CHANGELOG.md to the site's file collection as a generated page."""
    changelog = Path(config.config_file_path).parent / "CHANGELOG.md"
    files.append(File.generated(config, "changelog.md", content=changelog.read_text()))
    return files
