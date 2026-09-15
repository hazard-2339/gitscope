from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import git
from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from gitscope.models import CommitInfo


@dataclass
class NumstatEntry:
    insertions: int
    deletions: int
    sha: str
    path: str


class NotGitRepositoryError(Exception):
    """Raised when the provided path is not a valid Git repository."""


class GitRepoWrapper:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        try:
            self.repo: Repo = git.Repo(
                self.path,
                search_parent_directories=True,
            )
        except (InvalidGitRepositoryError, NoSuchPathError) as exc:
            raise NotGitRepositoryError(
                f"The path '{self.path}' is not a valid Git repository."
            ) from exc

    @property
    def active_branch_name(self) -> str:
        try:
            return self.repo.active_branch.name
        except TypeError:
            return f"detached at {self.repo.head.commit.hexsha[:7]}"

    def iter_commits(self, branch: str | None = None, since: str | None = None):
        rev = branch or self.active_branch_name
        if rev.startswith("DETACHED@"):
            rev = "HEAD"
        return list(self.repo.iter_commits(rev=rev, since=since))

    def branch_count(self) -> int:
        return len(list(self.repo.branches))

    def tag_count(self) -> int:
        return len(list(self.repo.tags))

    def commit_count(
        self,
        branch: str | None = None,
        since: str | None = None,
    ) -> int:
        return sum(1 for _ in self.iter_commits(branch=branch, since=since))

    def build_commit_info(self, commit: git.Commit) -> CommitInfo:
        stats = commit.stats.total

        return CommitInfo(
            sha=commit.hexsha,
            author_name=commit.author.name or "unknown",
            author_email=(commit.author.email or "unknown").lower(),
            committed_date=datetime.fromtimestamp(commit.committed_date),
            message=(
                commit.message.strip().splitlines()[0]
                if commit.message.strip()
                else ""
            ),
            is_merge=len(commit.parents) > 1,
            insertions=stats.get("insertions", 0),
            deletions=stats.get("deletions", 0),
            files_changed=stats.get("files", 0),
        )

    def numstat_entries(
        self,
        branch: str | None = None,
        since: str | None = None,
    ):
        rev = branch or self.active_branch_name

        if rev.startswith("DETACHED@"):
            rev = "HEAD"

        cmd = [
            "git",
            "-C",
            str(self.path),
            "log",
            "--no-color",
            "--pretty=format:@@%H",
            "--numstat",
            rev,
        ]

        if since:
            cmd.extend(["--since", since])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        current_sha = None

        for line in result.stdout.splitlines():
            if line.startswith("@@"):
                current_sha = line[2:].strip()
                continue

            if not line.strip() or current_sha is None:
                continue

            parts = line.split("\t")

            if len(parts) != 3:
                continue

            ins_raw, del_raw, path = parts

            if ins_raw == "-" or del_raw == "-":
                continue

            yield NumstatEntry(
                sha=current_sha,
                path=path,
                insertions=int(ins_raw),
                deletions=int(del_raw),
            )