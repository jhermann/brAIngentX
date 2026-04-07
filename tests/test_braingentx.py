"""Tests for the braingentx CLI safety guarantees."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def braingentx_module() -> types.ModuleType:
    """Load the CLI module with a stubbed pick dependency."""

    # Arrange
    module_path = Path(__file__).resolve().parents[1] / "bin" / "braingentx.py"
    spec = importlib.util.spec_from_file_location("braingentx_cli", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pick"] = types.SimpleNamespace(pick=lambda *args, **kwargs: [])

    assert spec is not None
    assert spec.loader is not None

    # Act
    spec.loader.exec_module(module)

    # Assert
    return module


def test_install_rejects_physical_directory(braingentx_module: types.ModuleType, tmp_path: Path) -> None:
    """Install refuses to replace a physical directory in the project."""

    # Arrange
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    source_dir = repo_root / ".agents" / "skills" / "demo"
    target_dir = project_root / ".agents" / "skills" / "demo"
    source_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    (source_dir / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    cli = braingentx_module.BrainGentX(repo_root=repo_root, project_root=project_root)
    item = braingentx_module.InstallableItem(name="demo", kind="skill", source=source_dir)

    # Act
    with pytest.raises(RuntimeError, match="refusing to replace physical path"):
        cli._install_skill("demo", item)

    # Assert
    assert target_dir.exists()
    assert not target_dir.is_symlink()


def test_installed_in_project_ignores_physical_paths(
    braingentx_module: types.ModuleType,
    tmp_path: Path,
) -> None:
    """Only symlinked skills and instructions count as installed."""

    # Arrange
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    cli = braingentx_module.BrainGentX(repo_root=repo_root, project_root=project_root)
    physical_skill = project_root / ".agents" / "skills" / "physical"
    physical_instruction = project_root / ".github" / "instructions" / "physical.instructions.md"
    linked_skill_target = repo_root / ".agents" / "skills" / "linked"
    linked_instruction_target = repo_root / ".github" / "instructions" / "linked.instructions.md"
    linked_skill = project_root / ".agents" / "skills" / "linked"
    linked_instruction = project_root / ".github" / "instructions" / "linked.instructions.md"

    physical_skill.mkdir(parents=True)
    physical_instruction.parent.mkdir(parents=True)
    physical_instruction.write_text("physical\n", encoding="utf-8")
    linked_skill_target.mkdir(parents=True)
    linked_instruction_target.parent.mkdir(parents=True)
    linked_instruction_target.write_text("linked\n", encoding="utf-8")
    linked_skill.parent.mkdir(parents=True, exist_ok=True)
    linked_instruction.parent.mkdir(parents=True, exist_ok=True)
    linked_skill.symlink_to(linked_skill_target, target_is_directory=True)
    linked_instruction.symlink_to(linked_instruction_target)

    # Act
    installed = cli._installed_in_project()

    # Assert
    assert installed == {"linked"}


def test_uninstall_keeps_physical_instruction_file(
    braingentx_module: types.ModuleType,
    tmp_path: Path,
) -> None:
    """Uninstall leaves a physical instruction file untouched."""

    # Arrange
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    cli = braingentx_module.BrainGentX(repo_root=repo_root, project_root=project_root)
    instruction_path = project_root / ".github" / "instructions" / "demo.instructions.md"
    instruction_path.parent.mkdir(parents=True)
    instruction_path.write_text("physical\n", encoding="utf-8")

    # Act
    cli._uninstall_skill("demo")

    # Assert
    assert instruction_path.exists()
    assert not instruction_path.is_symlink()


def test_cmd_install_updates_config_after_symlink_install(
    braingentx_module: types.ModuleType,
    tmp_path: Path,
) -> None:
    """Install records successfully linked skills in the project config."""

    # Arrange
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    skill_dir = repo_root / ".agents" / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    cli = braingentx_module.BrainGentX(repo_root=repo_root, project_root=project_root)

    # Act
    exit_code = cli.cmd_install(["demo"], pick=False)
    config = cli.load_project_config()
    target = project_root / ".agents" / "skills" / "demo"

    # Assert
    assert exit_code == 0
    assert target.is_symlink()
    assert config.installed == ["demo"]


def test_cmd_uninstall_removes_symlink_and_updates_config(
    braingentx_module: types.ModuleType,
    tmp_path: Path,
) -> None:
    """Uninstall removes a managed symlink and clears its config entry."""

    # Arrange
    repo_root = tmp_path / "repo"
    project_root = tmp_path / "project"
    skill_dir = repo_root / ".agents" / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# demo\n", encoding="utf-8")
    cli = braingentx_module.BrainGentX(repo_root=repo_root, project_root=project_root)
    cli.cmd_install(["demo"], pick=False)
    target = project_root / ".agents" / "skills" / "demo"

    # Act
    exit_code = cli.cmd_uninstall(["demo"], pick=False)
    config = cli.load_project_config()

    # Assert
    assert exit_code == 0
    assert not target.exists()
    assert config.installed == []
