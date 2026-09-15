from __future__ import annotations

from pathlib import Path

import pandas as pd

from gitscope.git_utils import GitRepoWrapper
from gitscope.models import CommitInfo, ContributorStats, FileChurn, RepoSummary


class GitRepoAnalyzer:
    """Analyze a Git repository and summarize commit and contributor activity."""

    def __init__(self, path: str | Path):
        self.repo = GitRepoWrapper(path)

    def analyze(
        self,
        branch: str | None = None,
        since: str | None = None,
        top_n_files: int = 10,
    ) -> RepoSummary:
        commits: list[CommitInfo] = [
            self.build_commit_info(commit)
            for commit in self.repo.iter_commits(branch=branch, since=since)
        ]

        summary = RepoSummary(
            repo_path=self.repo.path,
            active_branch=self.repo.active_branch_name,
            total_commits=len(commits),
            total_branches=self.repo.branch_count(),
            total_tags=self.repo.tag_count(),
        )

        if not commits:
            return summary

        summary.contributors = self.compute_contributor_stats(
            commits,
            top_n_files=top_n_files,
        )
        summary.top_files = self._file_hotspots(
            branch=branch,
            since=since,
            top_n=top_n_files,
        )
        summary.commits_by_day = self._commits_by_day(commits)

        return summary

    def build_commit_info(self, commit) -> CommitInfo:
        stats = getattr(commit, "stats", None)
        totals = getattr(stats, "total", {}) if stats is not None else {}

        return CommitInfo(
            sha=commit.hexsha,
            author_name=getattr(commit.author, "name", "unknown") or "unknown",
            author_email=(getattr(commit.author, "email", "unknown") or "unknown").lower(),
            committed_date=commit.committed_date,
            message=(commit.message.strip().splitlines()[0] if commit.message.strip() else ""),
            is_merge=len(commit.parents) > 1,
            insertions=totals.get("insertions", 0),
            deletions=totals.get("deletions", 0),
            files_changed=totals.get("files", 0),
        )

    def compute_contributor_stats(
        self,
        commits: list[CommitInfo],
        top_n_files: int,
    ) -> list[ContributorStats]:
        if not commits:
            return []

        df = pd.DataFrame(
            [
                {
                    "email": commit.author_email,
                    "name": commit.author_name,
                    "insertions": commit.insertions,
                    "deletions": commit.deletions,
                    "date": commit.committed_date,
                }
                for commit in commits
            ]
        )

        grouped = df.groupby("email").agg(
            name=("name", "first"),
            commit_count=("email", "count"),
            insertions=("insertions", "sum"),
            deletions=("deletions", "sum"),
            first_commit=("date", "min"),
            last_commit=("date", "max"),
        )
        grouped = grouped.sort_values("commit_count", ascending=False).head(top_n_files)

        return [
            ContributorStats(
                name=row.name_,
                email=email,
                commit_count=int(row.commit_count),
                insertions=int(row.insertions),
                deletions=int(row.deletions),
                first_commit=row.first_commit.to_pydatetime(),
                last_commit=row.last_commit.to_pydatetime(),
            )
            for email, row in zip(
                grouped.index,
                grouped.rename(columns={"name": "name_"}).itertuples(),
            )
        ]

    def _file_hotspots(
        self,
        branch: str | None,
        since: str | None,
        top_n: int,
    ) -> list[FileChurn]:
        rows = [
            {
                "path": entry.path,
                "insertions": entry.insertions,
                "deletions": entry.deletions,
            }
            for entry in self.repo.numstat_entries(branch=branch, since=since)
        ]

        if not rows:
            return []

        df = pd.DataFrame(rows)
        grouped = df.groupby("path").agg(
            times_changed=("path", "count"),
            insertions=("insertions", "sum"),
            deletions=("deletions", "sum"),
        )
        grouped["total_churn"] = grouped["insertions"] + grouped["deletions"]
        grouped = grouped.sort_values("total_churn", ascending=False).head(top_n)

        return [
            FileChurn(
                path=path,
                times_changed=int(row.times_changed),
                insertions=int(row.insertions),
                deletions=int(row.deletions),
            )
            for path, row in zip(grouped.index, grouped.itertuples())
        ]

    def _commits_by_day(
        self,
        commits: list[CommitInfo],
    ) -> dict[str, int]:
        df = pd.DataFrame({"date": [commit.committed_date for commit in commits]})
        df["day"] = df["date"].dt.strftime("%Y-%m-%d")
        counts = df.groupby("day").size().sort_index()
        return counts.to_dict()

        

    
