# Allows modern type hints such as `Path | None`.
from __future__ import annotations

# Lets us write exported reports as JSON files.
import json

# Lets us work safely with file and folder paths.
from pathlib import Path

# Optional means a value can be the stated type or None.
from typing import Optional

# Typer builds our command-line interface.
import typer

# Console prints styled text and progress messages in the terminal.
from rich.console import Console

# Import the package version from __init__.py.
from gitscope import __version__

# Import the class that analyzes Git repositories and its friendly error.
from gitscope.analyzer import GitRepoAnalyzer, NotAGitRepoError

# Import the final summary data model for type hints.
from gitscope.models import RepoSummary

# Import the class that prints the visual terminal report.
from gitscope.report import RichReportRenderer


# Create the main Typer application.
app = typer.Typer(
    # This becomes the command name shown in help text.
    name="gitscope",

    # This description appears when users run `gitscope --help`.
    help="Analyze any Git repository and generate engineering insights.",

    # Disable shell-completion setup because this small app does not need it.
    add_completion=False,
)

# Create one shared Rich console for messages and output.
console = Console()


# Run this function when the user provides the --version option.
def _version_callback(value: bool) -> None:
    # Do nothing if the --version option was not supplied.
    if not value:
        return

    # Print the version number in the terminal.
    console.print(f"gitscope {__version__}")

    # Stop the command successfully after printing the version.
    raise typer.Exit()


# Register options that belong to the main `gitscope` command.
@app.callback()
def main(
    # Define the --version flag.
    version: Optional[bool] = typer.Option(
        # None means the user did not provide this option.
        None,

        # The terminal flag users type.
        "--version",

        # Run this function as soon as Typer sees --version.
        callback=_version_callback,

        # Check this option before normal command processing.
        is_eager=True,

        # Explain the option in `gitscope --help`.
        help="Show the gitscope version and exit.",
    ),
) -> None:
    # This function registers global CLI options.
    # The `return` keeps the body intentionally empty.
    return


# Register `analyze` as a command: `gitscope analyze ...`.
@app.command()
def analyze(
    # The repository path is the first positional argument.
    path: Path = typer.Argument(
        # Use the current folder when no path is supplied.
        Path("."),

        # Reject paths that do not exist.
        exists=True,

        # A Git repository must be a folder, not a file.
        file_okay=False,

        # Explain this argument in the help screen.
        help="Path to the Git repository.",
    ),

    # --branch or -b lets a user select a branch to analyze.
    branch: Optional[str] = typer.Option(
        # None means use the current active branch.
        None,

        # Long form of the command option.
        "--branch",

        # Short form of the same command option.
        "-b",

        # Explain the option in the help screen.
        help="Branch to analyze (default: current branch).",
    ),

    # --since restricts the analysis to recent commits.
    since: Optional[str] = typer.Option(
        # None means do not apply a date filter.
        None,

        # The command option users type.
        "--since",

        # Explain what date formats GitScope accepts.
        help='Only include commits after this, e.g. "2 weeks ago".',
    ),

    # --top limits the number of contributors and files displayed.
    top: int = typer.Option(
        # Show ten results by default.
        10,

        # The command option users type.
        "--top",

        # Explain the option in the help screen.
        help="How many contributors / hotspot files to show.",
    ),

    # --export saves the finished analysis as JSON.
    export: Optional[Path] = typer.Option(
        # None means do not create an export file.
        None,

        # The command option users type.
        "--export",

        # Explain what this option does.
        help=(
            "Also write the summary as JSON to this path "
            "(e.g. reports/out.json)."
        ),
    ),
) -> None:
    """Analyze PATH and print a report to the terminal."""

    try:
        # Create the analyzer and validate that PATH is a Git repository.
        analyzer = GitRepoAnalyzer(path)

    # Show a friendly message instead of a technical traceback.
    except NotAGitRepoError as exc:
        # Print the error in bold red terminal text.
        console.print(f"[bold red]Error:[/bold red] {exc}")

        # Stop the command and tell the operating system it failed.
        raise typer.Exit(code=1)

    # Show a temporary progress message while Git history is being read.
    with console.status("[bold cyan]Walking commit history..."):
        # Run the complete analysis with the chosen options.
        summary = analyzer.analyze(
            branch=branch,
            since=since,
            top_n_files=top,
        )

    # Create the report renderer using our shared terminal console.
    renderer = RichReportRenderer(console=console)

    # Print the finished report.
    renderer.render(summary)

    # Export the report only when the user supplied --export.
    if export:
        # Save the summary as JSON.
        _export_json(summary, export)

        # Confirm where the JSON file was saved.
        console.print(
            f"\n[green]Saved JSON report to[/green] {export}"
        )


# Convert a RepoSummary into JSON and save it to a file.
def _export_json(
    summary: RepoSummary,
    export_path: Path,
) -> None:
    # Create the parent folder if it does not already exist.
    # For example, this creates reports/ for reports/summary.json.
    export_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Build a normal dictionary because json.dumps cannot directly
    # serialize dataclasses, Path objects, or datetime values.
    payload = {
        # Convert Path into text for JSON.
        "repo_path": str(summary.repo_path),

        # Keep the branch name.
        "active_branch": summary.active_branch,

        # Keep headline repository numbers.
        "total_commits": summary.total_commits,
        "total_branches": summary.total_branches,
        "total_tags": summary.total_tags,

        # Convert every ContributorStats object into a plain dictionary.
        "contributors": [
            {
                "name": contributor.name,
                "email": contributor.email,
                "commit_count": contributor.commit_count,
                "insertions": contributor.insertions,
                "deletions": contributor.deletions,

                # Convert datetime into JSON-safe ISO text when present.
                "first_commit": (
                    contributor.first_commit.isoformat()
                    if contributor.first_commit
                    else None
                ),

                # Convert datetime into JSON-safe ISO text when present.
                "last_commit": (
                    contributor.last_commit.isoformat()
                    if contributor.last_commit
                    else None
                ),
            }
            for contributor in summary.contributors
        ],

        # Convert every FileChurn object into a plain dictionary.
        "top_files": [
            {
                "path": file_churn.path,
                "times_changed": file_churn.times_changed,
                "insertions": file_churn.insertions,
                "deletions": file_churn.deletions,
            }
            for file_churn in summary.top_files
        ],

        # This is already a normal dictionary, so it can be stored directly.
        "commits_by_day": summary.commits_by_day,
    }

    # Turn the dictionary into nicely indented JSON and write it to disk.
    export_path.write_text(
        json.dumps(payload, indent=2)
    )


# Run the Typer command-line app only when this file is executed directly.
if __name__ == "__main__":
    app()