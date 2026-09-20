from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from gitscope.models import RepoSummary


class RichReportRenderer:
    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def render(self, summary: RepoSummary) -> None:
        self._render_header(summary)
        self.console.print()

        if summary.contributors:
            self._render_contributors(summary)
            self.console.print()

        if summary.top_files:
            self._render_hotspots(summary)
            self.console.print()

        if summary.commits_by_day:
            self._render_activity(summary)

    def _render_header(self, summary: RepoSummary) -> None:
        stats = Table.grid(
            expand=True,
            padding=(0, 4),
        )

        stats.add_column(justify="center")
        stats.add_column(justify="center")
        stats.add_column(justify="center")
        stats.add_column(justify="center")

        def stat_block(label: str, value: int | str) -> Text:
            block = Text()
            block.append(f"{value}\n", style="bold cyan")
            block.append(label, style="dim")
            return block

        stats.add_row(
            stat_block("Commits", summary.total_commits),
            stat_block("Branches", summary.total_branches),
            stat_block(
                "Contributors",
                summary.total_contributors,
            ),
            stat_block("Tags", summary.total_tags),
        )

        self.console.print(
            Panel(
                stats,
                title=(
                    "[bold]GitScope Analysis[/bold]"
                    f" -- {summary.repo_path.name}"
                ),
                subtitle=f"branch: {summary.active_branch}",
                box=box.ROUNDED,
            )
        )

    def _render_contributors(self, summary: RepoSummary) -> None:
        table = Table(
            title="Top Contributors",
            box=box.SIMPLE_HEAVY,
        )

        table.add_column("Name", style="bold")
        table.add_column("Email", style="dim")
        table.add_column("Commits", justify="right")
        table.add_column(
            "+Lines",
            justify="right",
            style="green",
        )
        table.add_column(
            "-Lines",
            justify="right",
            style="red",
        )

        for contributor in summary.contributors:
            table.add_row(
                contributor.name,
                contributor.email,
                str(contributor.commit_count),
                f"+{contributor.insertions}",
                f"-{contributor.deletions}",
            )

        self.console.print(table)

    def _render_hotspots(self, summary: RepoSummary) -> None:
        table = Table(
            title="File Hotspots (highest churn)",
            box=box.SIMPLE_HEAVY,
        )

        table.add_column("File", style="bold")
        table.add_column("Times Changed", justify="right")
        table.add_column(
            "Total Churn",
            justify="right",
            style="magenta",
        )

        for file_churn in summary.top_files:
            table.add_row(
                file_churn.path,
                str(file_churn.times_changed),
                str(file_churn.total_churn),
            )

        self.console.print(table)

    def _render_activity(self, summary: RepoSummary) -> None:
        days = list(summary.commits_by_day.items())[-14:]

        if not days:
            return

        max_count = max(count for _, count in days) or 1

        table = Table(
            title="Recent Commit Activity",
            box=box.SIMPLE,
        )

        table.add_column("Day")
        table.add_column("Commits")

        for day, count in days:
            bar_length = max(
                1,
                int((count / max_count) * 30),
            )

            table.add_row(
                day,
                "█" * bar_length + f"  {count}",
            )

        self.console.print(table)