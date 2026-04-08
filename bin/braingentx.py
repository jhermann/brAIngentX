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
        Interactively pick skills or instructions to install or uninstall.

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

    Any action changing local paths in the project (install, uninstall, restore, purge)
    will update the local configuration accordingly. Those actions will NEVER act on real
    physical files or directories, only on symlinks.

    The script refuses any action on its own repo, except `list`, `show`, and `info`.

    The `list` action includes available metadata like a frontmatter `description` or
    a H1 Markdown title.

    `show` pipes longer output through `less -R` if available. The environment variable
    `BRAINGENTX_PAGER` or `PAGER` are used when set, and parsed using `shlex.split`.

    Copilot instructions are also supported (in `.github/instructions/*.instructions.md`)
    and treated like skills. Skills are marked with 🛠️ and instructions with 🏛️.

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
PROJECT_CONFIG_FILE = Path(".agents") / "braingentx.ini"
PROJECT_INSTRUCTIONS_DIR = Path(".github") / "instructions"
SKILL_DOC_NAME = "SKILL.md"
INSTRUCTION_DOC_SUFFIX = ".instructions.md"
INFO_DESCR_MAXLEN = 88
PAGER_DEFAULT = ["less", "-R"]


def log_info(message: str) -> None:
    print(f"ℹ️  {message}")


def log_error(message: str) -> None:
    print(f"⚠️  {message}", file=sys.stderr)


@dataclass
class ProjectConfig:
    installed: list[str]
    schema_version: int = 1


@dataclass(frozen=True)
class InstallableItem:
    name: str
    kind: str
    source: Path

    @property
    def marker(self) -> str:
        return "🛠️" if self.kind == "skill" else "🏛️"

    @property
    def doc_path(self) -> Path:
        if self.kind == "skill":
            return self.source / SKILL_DOC_NAME
        return self.source


class BrainGentX:
    def __init__(self, repo_root: Path, project_root: Path, dry_run: bool = False) -> None:
        self.repo_root = repo_root
        self.project_root = project_root
        self.dry_run = dry_run
        self.project_skills_root = self.project_root / PROJECT_SKILLS_DIR
        self.project_instructions_root = self.project_root / PROJECT_INSTRUCTIONS_DIR
        self.project_config_path = self._resolve_project_config_path()

    def _ensure_gitignore_has_skills(self, skill_names: list[str]) -> None:
        """Ensure .gitignore contains the installed skill/instruction paths, at most once each."""
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            lines = []
        else:
            with gitignore_path.open("r", encoding="utf-8") as f:
                lines = f.readlines()
        # Normalize lines for comparison
        existing = set(line.strip() for line in lines if line.strip())
        to_add = []
        for name in skill_names:
            # Check if this is an instruction by checking for the file in the master repo
            instr_path_master = self.repo_root / ".github" / "instructions" / f"{name}.instructions.md"
            if instr_path_master.exists():
                instr_path = f".github/instructions/{name}.instructions.md"
                if instr_path not in existing:
                    to_add.append(instr_path)
            else:
                skill_path = f".agents/skills/{name}"
                if skill_path not in existing:
                    to_add.append(skill_path)
        if to_add:
            if self.dry_run:
                log_info(f"[dry-run] Would add to .gitignore: {', '.join(to_add)}")
            else:
                with gitignore_path.open("a", encoding="utf-8") as f:
                    for path in to_add:
                        f.write(f"\n{path}\n")
                log_info(f"Added to .gitignore: {', '.join(to_add)}")

    def _resolve_project_config_path(self) -> Path:
        return self.project_root / PROJECT_CONFIG_FILE

    def available_skills(self) -> dict[str, InstallableItem]:
        items: dict[str, InstallableItem] = {}
        skills_root = self.repo_root / PROJECT_SKILLS_DIR
        instructions_root = self.repo_root / PROJECT_INSTRUCTIONS_DIR

        if skills_root.is_dir():
            for entry in sorted(skills_root.iterdir()):
                if not entry.is_dir():
                    continue
                if (entry / SKILL_DOC_NAME).is_file():
                    items[entry.name] = InstallableItem(name=entry.name, kind="skill", source=entry)

        if instructions_root.is_dir():
            for entry in sorted(instructions_root.iterdir()):
                if not entry.is_file() or not entry.name.endswith(INSTRUCTION_DOC_SUFFIX):
                    continue

                name = entry.name.removesuffix(INSTRUCTION_DOC_SUFFIX)
                items[name] = InstallableItem(name=name, kind="instruction", source=entry)

        return items

    def load_project_config(self) -> ProjectConfig:
        if not self.project_config_path.exists():
            return ProjectConfig(installed=[])

        parser = configparser.ConfigParser()
        try:
            with self.project_config_path.open("r", encoding="utf-8") as handle:
                parser.read_file(handle)
        except (OSError, configparser.Error) as exc:
            raise RuntimeError(f"invalid INI project config in {self.project_config_path}: {exc}") from exc

        section = "braingentx"
        installed_text = parser.get(section, "installed", fallback="")
        installed = [item.strip() for item in installed_text.split(",") if item.strip()]

        return ProjectConfig(installed=sorted(set(installed)))

    def save_project_config(self, project_config: ProjectConfig) -> None:
        parser = configparser.ConfigParser()
        parser["braingentx"] = {
            "schema_version": "1",
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

        def marker_label(name: str) -> str:
            item = available.get(name)
            if item:
                return f"{item.marker} {name}"
            return name

        if pick:
            pick_usage = (
                " • Ctrl-C = abort"
                " • Space = Multi-select"
                " • Enter = confirm"
            )
            if action == "install":
                not_installed = sorted([name for name in available if name not in project_config.installed])
                pick_options = [marker_label(name) for name in not_installed]
                picked = self._pick_from_list(pick_options, "Pick skills or instructions to install" + pick_usage)
                # Map back to canonical names
                return [name.split(' ', 1)[1] if ' ' in name else name for name in picked]
            # For uninstall, show markers for installed
            pick_options = [marker_label(name) for name in sorted(project_config.installed)]
            picked = self._pick_from_list(pick_options, "Pick skills or instructions to uninstall" + pick_usage)
            return [name.split(' ', 1)[1] if ' ' in name else name for name in picked]

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
        import re
        import io
        try:
            import yaml
        except ImportError:
            yaml = None

        available = self.available_skills()
        installed = self._installed_in_project()
        repo_skills_root = self.repo_root / PROJECT_SKILLS_DIR
        repo_instructions_root = self.repo_root / PROJECT_INSTRUCTIONS_DIR

        if not available:
            log_info(
                "No skills or instructions found in repository: "
                f"{repo_skills_root} or {repo_instructions_root}"
            )
            return 0

        def extract_metadata(doc_path: Path) -> str:
            try:
                with doc_path.open("r", encoding="utf-8") as f:
                    lines = [next(f) for _ in range(30)]
            except (OSError, StopIteration):
                return ""
            text = "".join(lines)
            # Try YAML frontmatter
            heading_start = 0
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    yaml_block = text[3:end]
                    heading_start = end + 3  # skip past second ---
                    if yaml is not None:
                        try:
                            meta = yaml.safe_load(yaml_block)
                            desc = meta.get("description")
                            if desc:
                                return str(desc).strip()
                        except Exception:
                            pass
            # Only search for # heading after YAML frontmatter (after second ---)
            after_yaml = text[heading_start:]
            for line in after_yaml.splitlines():
                m = re.match(r"# (.+)", line)
                if m:
                    return m.group(1).strip()
            return ""

        def truncate(text: str, maxlen: int = INFO_DESCR_MAXLEN) -> str:
            if len(text) > maxlen:
                return text[:maxlen - 3].rstrip() + "..."
            return text

        heading = "Available skills (🛠️) and instructions (🏛️)"
        print(heading)
        print("‾" * len(heading))
        CYAN = "\033[96;1m"
        RESET = "\033[0m"
        for name in sorted(available):
            item = available[name]
            state_marker = "✅" if name in installed else "❌"
            meta = extract_metadata(item.doc_path)
            colored_name = f"{CYAN}{truncate(name)}{RESET}"
            if meta:
                print(f"  - {item.marker} {state_marker} {colored_name}: {truncate(meta)}")
            else:
                print(f"  - {item.marker} {state_marker} {colored_name}")

        return 0

    def cmd_show(self, name: str) -> int:
        import subprocess
        import shlex
        from io import StringIO

        available = self.available_skills()
        if name not in available:
            raise RuntimeError(f"unknown skill '{name}'")

        item = available[name]
        doc = item.doc_path
        output = StringIO()
        print(f"Name: {name}", file=output)
        print(f"Type: {item.kind}", file=output)
        print(f"Path: {item.source}", file=output)
        print("---", file=output)
        doc_text = doc.read_text(encoding="utf-8").strip()
        print(doc_text, file=output)
        value = output.getvalue()
        lines = value.splitlines()
        if len(lines) > 33:
            pager = os.environ.get("BRAINGENTX_PAGER") or os.environ.get("PAGER")
            if pager:
                pager_cmd = shlex.split(pager)
            else:
                pager_cmd = PAGER_DEFAULT
            try:
                proc = subprocess.Popen(pager_cmd, stdin=subprocess.PIPE)
                proc.communicate(input=value.encode("utf-8"))
            except Exception as e:
                print(value)
                print(f"[Warning] Could not pipe to pager: {e}", file=sys.stderr)
        else:
            print(value)
        return 0

    def _ensure_instructions_readme(self) -> None:
        """Ensure .github/instructions/README.md exists in the project, copying from master repo if needed."""
        src = self.repo_root / ".github" / "instructions" / "README.md"
        dst = self.project_root / ".github" / "instructions" / "README.md"
        if not dst.exists() and src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if self.dry_run:
                log_info(f"[dry-run] Would copy {src} to {dst}")
            else:
                import shutil
                shutil.copy2(src, dst)
                log_info(f"ℹ️ Copied {src} to {dst}")

    def cmd_install(self, names: list[str], pick: bool) -> int:
        self._ensure_instructions_readme()
        selected = self.resolve_install_names(names, pick=pick, action="install")
        if not selected:
            log_info("No skills selected.")
            return 0

        available = self.available_skills()
        project_config = self.load_project_config()
        # Remove already installed names
        to_install = [name for name in selected if name not in project_config.installed]
        if not to_install:
            log_info("All selected skills are already installed.")
            return 0

        for name in to_install:
            if name not in available:
                raise RuntimeError(f"unknown skill '{name}'")
            self._install_skill(name, available[name])
            project_config.installed = sorted(set(project_config.installed).union([name]))
            self.save_project_config(project_config)

        # Ensure .gitignore has the installed skill paths (after install)
        self._ensure_gitignore_has_skills(list(self._installed_in_project()))
        return 0

    def cmd_uninstall(self, names: list[str], pick: bool) -> int:
        project_config = self.load_project_config()
        selected = self.resolve_install_names(names, pick=pick, action="uninstall")
        if not selected:
            log_info("No skills selected.")
            return 0

        for name in selected:
            self._uninstall_skill(name)
            project_config.installed = [
                configured_name
                for configured_name in project_config.installed
                if configured_name != name
            ]
            self.save_project_config(project_config)

        return 0

    def cmd_restore(self) -> int:
        self._ensure_instructions_readme()
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

        # Ensure .gitignore has all wanted skill paths (after restore)
        self._ensure_gitignore_has_skills(list(self._installed_in_project()))
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
                "[dry-run] Would create default project config with no installed skills"
            )

        self.save_project_config(ProjectConfig(installed=[]))

        if not self.dry_run:
            log_info(f"Created default project config: {self.project_config_path}")

        return 0

    def cmd_info(self) -> int:
        project_config = self.load_project_config()
        available = self.available_skills()
        available_names = sorted(available)
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

        info("Master Root:", with_exists_marker(self.repo_root.resolve(), self.repo_root.is_dir()))
        info("Project Root:", with_exists_marker(self.project_root.resolve(), self.project_root.is_dir()))
        info("Skills Folder:",
             with_exists_marker(self.project_skills_root, self.project_skills_root.is_dir())
        )
        info(
            "Instructions Folder:",
            with_exists_marker(self.project_instructions_root, self.project_instructions_root.is_dir())
        )

        info(
            "Available Entries:",
            f"{len(available_names)} | {', '.join(f'{available[name].marker} {name}' for name in available_names) if available_names else '(none)'}",
        )
        info("Configured Skills:", f"{len(configured)} | {', '.join(configured) if configured else '(none)'}")
        info("Installed Skills:", f"{len(installed)} | {', '.join(installed) if installed else '(none)'}")
        info("Dry Run:", bool_marker(self.dry_run))

        info("Python:", f"{sys.executable} {platform.python_version()}")
        info("Platform:", platform.platform())
        info("Script File:", str(Path(__file__).resolve()))
        info("Current Working Dir:", str(Path.cwd()))

        return 0

    def _installed_in_project(self) -> set[str]:
        installed: set[str] = set()

        # Determine if we are in the master repo
        in_master_repo = self.project_root.resolve() == self.repo_root.resolve()

        if self.project_skills_root.is_dir():
            for entry in self.project_skills_root.iterdir():
                if in_master_repo:
                    # Accept both symlinks and real directories
                    if entry.is_symlink() or entry.is_dir():
                        installed.add(entry.name)
                else:
                    if entry.is_symlink():
                        installed.add(entry.name)

        if self.project_instructions_root.is_dir():
            for entry in self.project_instructions_root.iterdir():
                if in_master_repo:
                    if (entry.is_symlink() or entry.is_file()) and entry.name.endswith(INSTRUCTION_DOC_SUFFIX):
                        installed.add(entry.name.removesuffix(INSTRUCTION_DOC_SUFFIX))
                else:
                    if entry.is_symlink() and entry.name.endswith(INSTRUCTION_DOC_SUFFIX):
                        installed.add(entry.name.removesuffix(INSTRUCTION_DOC_SUFFIX))

        return installed

    def _install_skill(self, name: str, item: InstallableItem) -> None:
        target = self._project_target(item)
        if target.is_symlink():
            log_info(f"Replacing existing skill link '{name}'")
            if not self.dry_run:
                self._remove_path(target)
        elif target.exists():
            raise RuntimeError(
                f"refusing to replace physical path '{target}'; only symlinks can be managed"
            )

        if self.dry_run:
            log_info(f"[dry-run] Would install '{name}' -> {item.source}")
            return

        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(item.source, target, target_is_directory=item.kind == "skill")
            log_info(f"Installed '{name}'")
        except OSError as exc:
            raise RuntimeError(f"failed to create symlink '{target}': {exc}") from exc

    def _uninstall_skill(self, name: str) -> None:
        targets = [
            self.project_skills_root / name,
            self.project_instructions_root / f"{name}{INSTRUCTION_DOC_SUFFIX}",
        ]
        installed_targets = [target for target in targets if target.is_symlink()]

        if not installed_targets:
            log_info(f"Skill '{name}' is not installed")
            return

        if self.dry_run:
            log_info(f"[dry-run] Would uninstall '{name}'")
            return

        for target in installed_targets:
            self._remove_path(target)
        log_info(f"Uninstalled '{name}'")

    def _project_target(self, item: InstallableItem) -> Path:
        if item.kind == "skill":
            return self.project_skills_root / item.name
        return self.project_instructions_root / f"{item.name}{INSTRUCTION_DOC_SUFFIX}"

    def _remove_path(self, path: Path) -> None:
        if not path.is_symlink():
            raise RuntimeError(f"refusing to remove physical path '{path}'")

        path.unlink()


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
    install_parser.add_argument("-p", "--pick", action="store_true", help="Interactively pick skills or instructions")
    install_parser.add_argument("skills", nargs="*", help="Names of skills to install")

    subparsers.add_parser("list",
        help="List available skills and instructions,"
             " and their installation status in the project")

    show_parser = subparsers.add_parser("show", help="Show details for one skill")
    show_parser.add_argument("skill", help="Name of the skill")

    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall skills from the project")
    uninstall_parser.add_argument("-p", "--pick", action="store_true", help="Interactively pick skills or instructions")
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
