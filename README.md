# GitScope 🔬

A Git intelligence CLI — point it at any Git repository and it tells you
who's contributing, which files are the hottest churn points, and how
activity has trended over time. Output is a clean terminal report built
with [Rich](https://github.com/Textualize/rich):

```<img width="718" height="902" alt="Screenshot 2026-09-20 221414" src="https://github.com/user-attachments/assets/dd3e63b6-1d4a-4fd1-aafe-d5ec90896047" />

╭──────────────────── GitScope Analysis -- myrepo ─────────────────────╮
│      842            18              9              5                 │
│    Commits       Branches      Contributors       Tags                │
╰──────────────────────── branch: main ─────────────────────────────────╯

                          Top Contributors
  Name          Email                    Commits   +Lines   -Lines
  Ada Lovelace  ada@example.com               612    +9,201   -2,340

                    File Hotspots (highest churn)
  File                        Times Changed   Total Churn
  src/gitscope/cli.py                    41            980

              Recent Commit Activity
  Day          Commits
  2026-09-18   ██████████████████████████████  6
```

---

## Table of contents

- [Why this project exists](#why-this-project-exists)
- [Folder structure](#folder-structure)
- [Architecture: how the pieces fit together](#architecture-how-the-pieces-fit-together)
- [Install](#install)
- [Usage](#usage)
- [Reading the output](#reading-the-output)
- [Customizing the output](#customizing-the-output)
- [Testing](#testing)
- [CI](#ci-github-actions)
- [Troubleshooting](#troubleshooting)
- [Extending it further](#extending-it-further)

---

## Why this project exists

It's a compact but "real" showcase of:

- **Advanced Python** — dataclasses, `pathlib`, type hints, a Typer CLI
- **Git internals** — walking the commit graph, telling merge commits from
  regular ones, reading `--numstat` diff data, branches vs. tags
- **Data analysis** — using `pandas.groupby()` to turn raw commit rows into
  per-author and per-file statistics
- **Terminal UI** — Rich panels/tables for a genuinely nice-looking CLI
- **Testing** — a small, deliberate pytest suite using a real throwaway repo
- **CI** — a GitHub Actions workflow that runs the suite + a CLI smoke test

## Folder structure

```
gitscope/
├── src/
│   └── gitscope/
│       ├── __init__.py     # package version + re-exports
│       ├── models.py       # dataclasses: CommitInfo, ContributorStats, FileChurn, RepoSummary
│       ├── git_utils.py    # the ONLY file that talks to Git (GitPython + subprocess)
│       ├── analyzer.py     # raw git data -> statistics (uses pandas)
│       ├── report.py       # statistics -> pretty terminal output (uses Rich)
│       └── cli.py          # command-line entry point (uses Typer), wires it all together
├── tests/
│   └── test_analyzer.py    # a handful of tests against a real throwaway git repo
├── reports/                 # default output folder for --export'ed JSON reports
├── .github/workflows/ci.yml # GitHub Actions: install, test, smoke-test the CLI
├── pyproject.toml
└── README.md
```

`tests/` sits **next to** `src/`, not inside it — pytest and the editable
install both assume this layout. If `tests/` ever ends up nested under
`src/gitscope/`, move it back out; that's a real bug, not a style choice.

## Architecture: how the pieces fit together

Dependencies only ever flow one way:

```
cli.py  --calls-->  analyzer.py  --calls-->  git_utils.py  --calls-->  .git/
   |                     |
   '--calls--> report.py '
```

Nothing below a layer knows about the layer above it:

| File | Knows about | Never imports |
|---|---|---|
| `models.py` | nothing (pure data shapes) | pandas, Rich, Typer, git |
| `git_utils.py` | GitPython, subprocess, `models.py` | pandas, Rich, Typer |
| `analyzer.py` | `git_utils.py`, `models.py`, pandas | Rich, Typer |
| `report.py` | `models.py`, Rich | Typer, git |
| `cli.py` | everything (it's the entry point) | — |

This is why `analyzer.py` can be unit-tested without a terminal, and why
swapping Rich for something else would never touch the analysis logic.

**Where each piece of data comes from, concretely:**

- `GitRepoWrapper` (in `git_utils.py`) opens the repo with GitPython
  (`Repo(path, search_parent_directories=True)`) and exposes:
  - `iter_commits(branch, since)` — walks the commit graph
  - `build_commit_info(commit)` — converts one raw GitPython `Commit` into
    our own `CommitInfo` dataclass (this is the **only** place that should
    ever construct a `CommitInfo` — see [Troubleshooting](#troubleshooting)
    for what goes wrong when that rule gets broken)
  - `numstat_entries(branch, since)` — shells out to `git log --numstat`
    directly, because asking GitPython for per-file stats per-commit is
    much slower on large histories
  - `branch_count()`, `tag_count()`, `active_branch_name`

- `GitRepoAnalyzer` (in `analyzer.py`) calls the wrapper, then uses pandas
  `groupby()` to turn the raw rows into:
  - `_contributor_stats` — grouped by author **email** (more stable than
    display name across machines)
  - `_file_hotspots` — grouped by file path, ranked by total churn
  - `_commits_by_day` — bucketed by calendar day for the activity chart

- `RichReportRenderer` (in `report.py`) takes the finished `RepoSummary`
  and prints it — header panel, contributors table, hotspots table,
  activity chart — each as its own method.

## Install

```bash
cd gitscope
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

This installs GitPython, Rich, pandas, Typer, pytest, and registers a
`gitscope` command on your PATH pointing at `src/gitscope/cli.py`.

## Usage

```bash
# analyze the repo you're standing in
gitscope analyze .

# analyze a different repo
gitscope analyze /path/to/other/repo

# only look at recent history
gitscope analyze . --since "3 months ago"

# a specific branch (must already exist locally — see Troubleshooting)
gitscope analyze . --branch develop

# fewer rows in the contributors/hotspots tables
gitscope analyze . --top 5

# also save the results as JSON
gitscope analyze . --export reports/summary.json

# check the version
gitscope --version
```

The target folder has to be inside a real git repository (`git init` it
first if it isn't) — pointing at a plain folder raises a clean
`NotAGitRepoError` instead of a stack trace.

## Reading the output

**Header panel** — `Commits` (total reachable from the analyzed branch),
`Branches` (**local** branches only, `refs/heads/*` — remote-tracking
branches are deliberately excluded so a fresh clone doesn't inflate the
count), `Contributors` (distinct **emails**, not names), `Tags`.

**Top Contributors** — commit count, lines added/removed per person,
sorted by commit count descending. Grouped by email rather than display
name because the same person's name is often typed inconsistently across
machines, but their configured email tends to be more stable — the same
heuristic `git shortlog -sne` uses.

**File Hotspots** — files ranked by total churn (insertions + deletions
summed across their whole history). High-churn files are either actively
evolving hotspots or poorly-factored files that keep needing patches;
either way, worth a look.

**Recent Commit Activity** — a simple bar chart of commits per day, the
most recent 14 days, scaled so the busiest day fills the bar.

## Customizing the output

**No code changes — CLI flags:**
```bash
gitscope analyze . --since "2 weeks ago" --top 3 --export reports/out.json
```

**Change what's displayed — edit `report.py`.** Each section is its own
method on `RichReportRenderer`: `_render_header`, `_render_contributors`,
`_render_hotspots`, `_render_activity`. Add/remove a column by editing the
matching `table.add_column(...)` / `table.add_row(...)` pair. Change
colors via `style="bold red"` etc., or `box=box.ROUNDED` / `box.SIMPLE` /
`box.DOUBLE` for a different table border style. To drop a whole section,
comment out its call inside `render()`.

**Change what's computed — edit `analyzer.py` + `models.py`.** Add a new
field to the relevant dataclass in `models.py`, populate it in
`GitRepoAnalyzer.analyze()` (or a new helper method), then render it in
`report.py`. Because of the layering above, this never requires touching
`git_utils.py` unless the new metric needs raw data that isn't already
being pulled from git.

**Different export format.** `cli.py`'s `_export_json` already builds a
plain dict and writes JSON. For CSV, pandas makes it close to free — the
contributor/file-hotspot methods in `analyzer.py` already build a
DataFrame before converting it to dataclasses; add `df.to_csv(path)`
right there for a one-line export path.

## Testing

Kept deliberately minimal by design: three focused tests in
`tests/test_analyzer.py`, using a real throwaway git repo built in a temp
directory (`git init` + `git commit`, via pytest's `tmp_path` fixture)
rather than mocks. They prove the core pipeline
(`git_utils -> analyzer -> models`) works end-to-end, not full coverage.

```bash
pytest -v
```

## CI (GitHub Actions)

`.github/workflows/ci.yml` runs on every push/PR to `main`: installs the
package on Python 3.10 and 3.12, runs `pytest -v`, then runs
`gitscope analyze .` against the checkout itself as a smoke test — catching
import errors or missing files that unit tests alone might not.

## Troubleshooting

A few issues came up while building this out — noting them here since
they're easy to hit again when extending the code by hand:

- **`ImportError: cannot import name 'X' from 'gitscope.Y'`** — almost
  always a name mismatch between where something is *defined* and where
  it's *imported*. Grep for the exact name across every file:
  ```bash
  # PowerShell
  Select-String -Path src\gitscope\*.py -Pattern "TheNameInQuestion"
  # macOS/Linux
  grep -rn "TheNameInQuestion" src/gitscope/
  ```
  and make sure the defining file and every importing file agree on the
  exact spelling.

- **`TypeError: ...got an unexpected keyword argument`** — same root
  cause, but for function/method parameter names instead of class names.
  Check the function's actual signature (`Select-String -Pattern "def the_func"`)
  against every call site.

- **`AttributeError: 'int' object has no attribute 'to_pydatetime'`** —
  means a `datetime` field somewhere is still holding a raw Unix
  timestamp instead of a converted `datetime` object. `CommitInfo` should
  only ever be constructed in one place (`GitRepoWrapper.build_commit_info`
  in `git_utils.py`, using `datetime.fromtimestamp(commit.committed_date)`).
  If `analyzer.py` ever grows its own second copy of that construction
  logic, delete the duplicate and call `self.repo.build_commit_info(...)`
  instead — two copies of the same logic drifting apart was the actual
  cause of this one.

- **`GitCommandError: ... fatal: bad revision '<branch>'`** when using
  `--branch` — not a bug, this means that branch name doesn't exist
  locally. Check with `git branch`, and remember `--branch` only accepts
  branches that exist in the repo you're pointing `gitscope` at.

- **A fix "doesn't take"** — after editing a file, confirm the change is
  actually saved before re-running:
  ```powershell
  Select-String -Path src\gitscope\the_file.py -Pattern "the_thing_you_changed"
  ```
  then clear any stale bytecode cache before retrying:
  ```powershell
  Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
  ```

## Extending it further

- `git_utils.py`: add blame-based stats (`git blame --line-porcelain`) to
  see which author "owns" the most current lines, not just historical
  commits.
- `git_utils.py`: give `iter_commits` a friendly error when `branch`
  doesn't exist locally, mirroring how the constructor already raises
  `NotAGitRepoError` for a bad path — right now a nonexistent `--branch`
  surfaces a raw `GitCommandError` traceback instead.
- `analyzer.py`: detect rebases/force-pushes by comparing reflog entries.
- `report.py`: add a `--format json` / `--format csv` flag using pandas'
  own `DataFrame.to_csv()`.
