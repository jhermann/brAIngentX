#! /usr/bin/env python3
""" Skills sharing for an agentic age.

    This tool allows projects to install or activate skills from a checkout of
    this repository. It is meant to be used by developers to manage a project-local
    configuration and links to skills that can be centrally managed that way.
    
    ----
    Usage:

    General options:

    --help, -h
        Show this help message and exit.
    
    -n, --dry-run
        Show what would be done, but don't actually do it.

    --p, --pick
        Interactively pick skills to install or uninstall.

    ```bash
    # Install skills from this repository into the project
    braingentx install [--pick | <skill-name> [<skill-name> ...]]

    # List all available skills in the repository, and their installation status in the project
    braingentx list

    # Show details about a specific skill
    braingentx show <skill-name>

    # Uninstall a skill from the project
    braingentx uninstall [--pick | <skill-name> [<skill-name> ...]]

    # Restore skills from the local configuration, installing missing ones and uninstalling removed ones
    braingentx restore

    # Remove all installed skills from the project, but keep the local configuration
    braingentx purge

    # Generate a default project-local config file at the standard location
    braingentx mkcfg

    # Show system information for debugging
    braingentx info
    ```

    The project-local configuration is stored in a "braingentx.ini" file
    in the ".agents/skills" directory of the project.

    The script refuses any action on its own repo, except `list`, `show`, and `info`.

    ----
    This script should not require any special OS or Python packages except the ones listed here:

        - Python 3.10 or higher
        - pick (for interactive selection)

    When the additional Python packages are not available, the script will print a helpful message and exit,
    instructing the user on how to install the missing dependencies into their user site.

    ----
    Copyright ©️ 2026 Jürgen Hermann

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

from __future__ import annotations

import os
import sys
import shutil
import platform
import argparse
import configparser
from typing import Iterable
from pathlib import Path
from dataclasses import dataclass

try:
    from pick import pick
except ImportError as exc:
    print(f"{exc}\n\nThe 'pick' package is required for braingentx to run."
          "\n\nPlease install it with:\n"
          "    pip install --user pick", file=sys.stderr)
    sys.exit(1)

PROJECT_SKILLS_DIR = Path(".agents") / "skills"
PROJECT_CONFIG_FILE = PROJECT_SKILLS_DIR / "braingentx.ini"
SKILLS_DIR_NAME = "skills"
SKILL_DOC_NAME = "SKILL.md"


def log_info(message: str) -> None:
    print(f"ℹ️  {message}")


def log_error(message: str) -> None:
    print(f"⚠️  {message}", file=sys.stderr)


@dataclass
class ProjectConfig:
    repo_root: str
    installed: list[str]
    schema_version: int = 1


class BrainGentX:
    def __init__(self, repo_root: Path, project_root: Path, dry_run: bool = False) -> None:
        self.repo_root = repo_root
        self.project_root = project_root
        self.dry_run = dry_run
        self.skills_root = self.repo_root / SKILLS_DIR_NAME
        self.project_skills_root = self.project_root / PROJECT_SKILLS_DIR
        self.project_config_path = self._resolve_project_config_path()

    def _resolve_project_config_path(self) -> Path:
        return self.project_root / PROJECT_CONFIG_FILE

    def available_skills(self) -> dict[str, Path]:
        skills: dict[str, Path] = {}
        if not self.skills_root.is_dir():
            return skills

        for entry in sorted(self.skills_root.iterdir()):
            if not entry.is_dir():
                continue
            if (entry / SKILL_DOC_NAME).is_file():
                skills[entry.name] = entry

        return skills

    def load_project_config(self) -> ProjectConfig:
        if not self.project_config_path.exists():
            return ProjectConfig(repo_root=str(self.repo_root), installed=[])

        parser = configparser.ConfigParser()
        try:
            with self.project_config_path.open("r", encoding="utf-8") as handle:
                parser.read_file(handle)
        except (OSError, configparser.Error) as exc:
            raise RuntimeError(f"invalid INI project config in {self.project_config_path}: {exc}") from exc

        section = "braingentx"
        repo_root = parser.get(section, "repo_root", fallback=str(self.repo_root))
        installed_text = parser.get(section, "installed", fallback="")
        installed = [item.strip() for item in installed_text.split(",") if item.strip()]

        return ProjectConfig(repo_root=repo_root, installed=sorted(set(installed)))

    def save_project_config(self, project_config: ProjectConfig) -> None:
        parser = configparser.ConfigParser()
        parser["braingentx"] = {
            "schema_version": "1",
            "repo_root": project_config.repo_root,
            "installed": ", ".join(sorted(set(project_config.installed))),
        }
        if self.dry_run:
            log_info(f"[dry-run] Would write {self.project_config_path}")
            return

        self.project_config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.project_config_path.open("w", encoding="utf-8") as handle:
            parser.write(handle)

    def resolve_install_names(self, names: Iterable[str] | None, pick: bool, action: str) -> list[str]:
        available = self.available_skills()
        project_config = self.load_project_config()

        if pick:
            if action == "install":
                return self._pick_from_list(sorted(available), "Pick skills to install")
            return self._pick_from_list(sorted(project_config.installed), "Pick skills to uninstall")

        selected = sorted(set(names or []))
        if not selected:
            raise RuntimeError("no skills selected; provide names or use --pick")

        return selected

    def _pick_from_list(self, items: list[str], title: str) -> list[str]:
        if not items:
            return []

        selected = pick(items, title, multiselect=True, min_selection_count=0)
        if not selected:
            return []

        return sorted(name for name, _ in selected)

    def cmd_list(self) -> int:
        available = self.available_skills()
        installed = self._installed_in_project()

        if not available:
            log_info(f"No skills found in repository: {self.skills_root}")
            return 0

        print("Available skills:")
        for name in sorted(available):
            marker = "installed" if name in installed else "not installed"
            print(f"  - {name}: {marker}")

        return 0

    def cmd_show(self, name: str) -> int:
        available = self.available_skills()
        if name not in available:
            raise RuntimeError(f"unknown skill '{name}'")

        skill_dir = available[name]
        doc = skill_dir / SKILL_DOC_NAME
        print(f"Name: {name}")
        print(f"Path: {skill_dir}")
        print("---")
        print(doc.read_text(encoding="utf-8").strip())
        return 0

    def cmd_install(self, names: list[str], pick: bool) -> int:
        selected = self.resolve_install_names(names, pick=pick, action="install")
        if not selected:
            log_info("No skills selected.")
            return 0

        available = self.available_skills()
        project_config = self.load_project_config()

        for name in selected:
            if name not in available:
                raise RuntimeError(f"unknown skill '{name}'")
            self._install_skill(name, available[name])

        project_config.installed = sorted(set(project_config.installed).union(selected))
        project_config.repo_root = str(self.repo_root)
        self.save_project_config(project_config)
        return 0

    def cmd_uninstall(self, names: list[str], pick: bool) -> int:
        project_config = self.load_project_config()
        selected = self.resolve_install_names(names, pick=pick, action="uninstall")
        if not selected:
            log_info("No skills selected.")
            return 0

        for name in selected:
            self._uninstall_skill(name)

        project_config.installed = [name for name in project_config.installed if name not in set(selected)]
        self.save_project_config(project_config)
        return 0

    def cmd_restore(self) -> int:
        project_config = self.load_project_config()
        wanted = set(project_config.installed)
        available = self.available_skills()
        currently_installed = self._installed_in_project()

        for name in sorted(wanted - currently_installed):
            if name not in available:
                log_error(f"Configured skill '{name}' no longer exists in repository; skipping")
                continue
            self._install_skill(name, available[name])

        for name in sorted(currently_installed - wanted):
            self._uninstall_skill(name)

        return 0

    def cmd_purge(self) -> int:
        project_config = self.load_project_config()
        for name in sorted(set(project_config.installed)):
            self._uninstall_skill(name)
        return 0

    def cmd_mkcfg(self) -> int:
        if self.project_config_path.exists():
            log_info(f"Project config already exists: {self.project_config_path}")
            return 0

        if self.dry_run:
            log_info(
                "[dry-run] Would create default project config with "
                f"repo_root='{self.repo_root}' and no installed skills"
            )

        self.save_project_config(ProjectConfig(repo_root=str(self.repo_root), installed=[]))

        if not self.dry_run:
            log_info(f"Created default project config: {self.project_config_path}")

        return 0

    def cmd_info(self) -> int:
        project_config = self.load_project_config()
        available = sorted(self.available_skills())
        installed = sorted(self._installed_in_project())
        configured = sorted(set(project_config.installed))
        repo_env = os.environ.get("BRAINGENTX_REPO")

        bold = "\033[1m"
        reset = "\033[0m"
        label_width = 3 * 8

        def info(label: str, value: str) -> None:
            print(f"{bold}{label.ljust(label_width)}{reset} {value}")

        def bool_marker(value: bool) -> str:
            return "☑️" if value else "⛔"

        def with_exists_marker(value: object, exists: bool | None = None) -> str:
            if exists is None and isinstance(value, Path):
                exists = value.exists()
            if exists is None:
                exists = bool(value)
            marker = "✅" if exists else "❌"
            return f"{marker} {value}"

        info(
            "Project Config Path:",
            with_exists_marker(self.project_config_path, self.project_config_path.is_file()),
        )
        info("Repo Env Override:", repo_env or "(BRAINGENTX_REPO is unset)")
        info("Configured Repo Root:", project_config.repo_root)

        info("Repo Root:", with_exists_marker(self.repo_root.resolve(), self.repo_root.is_dir()))
        info("Skills Root:", with_exists_marker(self.skills_root, self.skills_root.is_dir()))
        info(
            "Project Skills Root:",
            with_exists_marker(self.project_skills_root, self.project_skills_root.is_dir()),
        )
        info("Project Root:", with_exists_marker(self.project_root.resolve(), self.project_root.is_dir()))

        info("Available Skills:", f"{len(available)} | {', '.join(available) if available else '(none)'}")
        info("Configured Skills:", f"{len(configured)} | {', '.join(configured) if configured else '(none)'}")
        info("Installed Skills:", f"{len(installed)} | {', '.join(installed) if installed else '(none)'}")
        info("Dry Run:", bool_marker(self.dry_run))

        info("Python:", f"{sys.executable} {platform.python_version()}")
        info("Platform:", platform.platform())
        info("Script File:", str(Path(__file__).resolve()))
        info("Current Working Dir:", str(Path.cwd()))

        return 0

    def _installed_in_project(self) -> set[str]:
        if not self.project_skills_root.is_dir():
            return set()

        installed: set[str] = set()
        for entry in self.project_skills_root.iterdir():
            if entry.is_symlink() or entry.is_dir():
                installed.add(entry.name)
        return installed

    def _install_skill(self, name: str, source: Path) -> None:
        target = self.project_skills_root / name
        if target.exists() or target.is_symlink():
            log_info(f"Replacing existing skill link '{name}'")
            if not self.dry_run:
                self._remove_path(target)

        if self.dry_run:
            log_info(f"[dry-run] Would install '{name}' -> {source}")
            return

        self.project_skills_root.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(source, target, target_is_directory=True)
            log_info(f"Installed '{name}'")
        except OSError:
            # Fallback for systems where symlinks are unavailable.
            shutil.copytree(source, target)
            log_info(f"Installed '{name}' (copied)")

    def _uninstall_skill(self, name: str) -> None:
        target = self.project_skills_root / name
        if not (target.exists() or target.is_symlink()):
            log_info(f"Skill '{name}' is not installed")
            return

        if self.dry_run:
            log_info(f"[dry-run] Would uninstall '{name}'")
            return

        self._remove_path(target)
        log_info(f"Uninstalled '{name}'")

    def _remove_path(self, path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink()
            return
        shutil.rmtree(path)


def detect_repo_root() -> Path:
    env_root = os.environ.get("BRAINGENTX_REPO")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def build_parser() -> argparse.ArgumentParser:
    description = (__doc__ or "braingentx").split("----")[0]
    parser = argparse.ArgumentParser(prog="braingentx", description=description)
    parser.add_argument("-n", "--dry-run", action="store_true", help="Show what would be done")
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser("install", help="Install skills into the project")
    install_parser.add_argument("-p", "--pick", action="store_true", help="Interactively pick skills")
    install_parser.add_argument("skills", nargs="*", help="Names of skills to install")

    subparsers.add_parser("list", help="List available skills")

    show_parser = subparsers.add_parser("show", help="Show details for one skill")
    show_parser.add_argument("skill", help="Name of the skill")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall skills from the project")
    uninstall_parser.add_argument("-p", "--pick", action="store_true", help="Interactively pick skills")
    uninstall_parser.add_argument("skills", nargs="*", help="Names of skills to uninstall")

    subparsers.add_parser("restore", help="Reconcile installed skills with local project config")
    subparsers.add_parser("purge", help="Uninstall all configured skills")
    subparsers.add_parser("mkcfg", help="Generate a default project-local config file")
    subparsers.add_parser("info", help="Show system information for debugging")

    return parser


def run(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    project_root = Path.cwd()
    repo_root = detect_repo_root()

    allowed_on_own_repo = {"list", "show", "info"}
    if project_root.resolve() == repo_root.resolve() and args.command not in allowed_on_own_repo:
        allowed = ", ".join(sorted(allowed_on_own_repo))
        raise RuntimeError(
            "refusing this action in the brAIngentX repository itself; "
            f"allowed commands here: {allowed}"
        )

    cli = BrainGentX(repo_root=repo_root, project_root=project_root, dry_run=args.dry_run)

    if args.command == "install":
        return cli.cmd_install(args.skills, pick=args.pick)
    elif args.command == "list":
        return cli.cmd_list()
    elif args.command == "show":
        return cli.cmd_show(args.skill)
    elif args.command == "uninstall":
        return cli.cmd_uninstall(args.skills, pick=args.pick)
    elif args.command == "restore":
        return cli.cmd_restore()
    elif args.command == "purge":
        return cli.cmd_purge()
    elif args.command == "mkcfg":
        return cli.cmd_mkcfg()
    elif args.command == "info":
        return cli.cmd_info()

    parser.print_help()
    return 1


def main() -> int:
    try:
        return run(sys.argv[1:])
    except RuntimeError as exc:
        log_error(str(exc))
        return 2
    except KeyboardInterrupt:
        log_error("Interrupted")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
