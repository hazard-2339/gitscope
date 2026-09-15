from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class CommitInfo:
    sha: str
    author_name: str
    author_email: str
    committed_date: datetime
    message: str
    is_merge: bool
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0


@dataclass
class ContributorStats:
    name: str
    email: str
    commit_count: int = 0
    insertions: int = 0
    deletions: int = 0
    first_commit: datetime | None = None
    last_commit: datetime | None = None

    @property
    def net_lines(self) -> int:
        return self.insertions - self.deletions


@dataclass
class FileChurn:
    path: str
    times_changed: int = 0
    insertions: int = 0
    deletions: int = 0

    @property
    def total_churn(self) -> int:
        return self.insertions + self.deletions


@dataclass
class RepoSummary:
    repo_path: Path
    active_branch: str
    total_commits: int
    total_branches: int
    total_tags: int
    contributors: list[ContributorStats] = field(default_factory=list)
    top_files: list[FileChurn] = field(default_factory=list)
    commits_by_day: dict[str, int] = field(default_factory=dict)

    @property
    def total_contributors(self) -> int:
        return len(self.contributors)