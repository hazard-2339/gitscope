import subprocess
from pathlib import Path

import pytest

from gitscope.analyzer import GitRepoAnalyzer, NotAGitRepoError


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "tiny_repo"
    repo_dir.mkdir()

    _run(
        ["git", "init", "-q", "-b", "main"],
        cwd=repo_dir,
    )

    _run(
        ["git", "config", "user.email", "ada@example.com"],
        cwd=repo_dir,
    )

    _run(
        ["git", "config", "user.name", "Ada Lovelace"],
        cwd=repo_dir,
    )

    (repo_dir / "README.md").write_text("# Tiny Repo\n")

    _run(
        ["git", "add", "README.md"],
        cwd=repo_dir,
    )

    _run(
        ["git", "commit", "-q", "-m", "Initial commit"],
        cwd=repo_dir,
    )

    (repo_dir / "main.py").write_text(
        "print('hello world')\n"
    )

    _run(
        ["git", "add", "main.py"],
        cwd=repo_dir,
    )

    _run(
        ["git", "commit", "-q", "-m", "Add main.py"],
        cwd=repo_dir,
    )

    return repo_dir


def test_analyze_counts_commits_and_branch(
    tiny_repo: Path,
) -> None:
    summary = GitRepoAnalyzer(tiny_repo).analyze()

    assert summary.total_commits == 2
    assert summary.total_branches == 1
    assert summary.active_branch == "main"


def test_analyze_finds_the_single_contributor(
    tiny_repo: Path,
) -> None:
    summary = GitRepoAnalyzer(tiny_repo).analyze()

    assert summary.total_contributors == 1

    ada = summary.contributors[0]

    assert ada.email == "ada@example.com"
    assert ada.commit_count == 2


def test_non_git_directory_raises(
    tmp_path: Path,
) -> None:
    plain_dir = tmp_path / "not_a_repo"
    plain_dir.mkdir()

    with pytest.raises(NotAGitRepoError):
        GitRepoAnalyzer(plain_dir)