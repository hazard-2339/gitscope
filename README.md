# GitScope 🔬

GitScope is a Python command-line tool that analyzes a Git repository and produces engineering insights.

It shows:

- Total commits, branches, tags, and contributors
- The most active contributors
- Files with the highest amount of change
- Recent commit activity

## Project structure

```text
gitscope/
├── pyproject.toml
├── README.md
├── src/
│   └── gitscope/
│       ├── __init__.py
│       ├── models.py
│       ├── git_utils.py
│       ├── analyzer.py
│       ├── report.py
│       └── cli.py
└── tests/
    ├── __init__.py
    └── test_analyzer.py
```

```text
cli.py
    ↓
analyzer.py
    ↓
git_utils.py
    ↓
Git repository
    ↓
models.py
    ↓
report.py
    ↓
Terminal report
```

- `cli.py` receives commands and options from the user.
- `git_utils.py` reads commits, branches, tags, and file changes from Git.
- `analyzer.py` calculates contributor statistics and file churn.
- `models.py` defines the data objects passed between files.
- `report.py` displays the final result with Rich.
- `test_analyzer.py` verifies the analysis with a temporary Git repository.

## Requirements

- Python 3.10 or newer
- Git installed and available in your terminal
- VS Code, recommended for development

## Installation

Open the GitScope folder in VS Code, then open the integrated terminal with:

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install GitScope and its development dependencies:

```bash
python -m pip install -e ".[dev]"
```

The `-e` means “editable install.” Changes you make to files in `src\gitscope` are used immediately without reinstalling the project.

## Run GitScope

Analyze the Git repository in the current folder:

```bash
gitscope analyze .
```

Analyze a different repository:

```bash
gitscope analyze C:\path\to\another\repository
```

Analyze one branch:

```bash
gitscope analyze . --branch main
```

Analyze only recent commits:

```bash
gitscope analyze . --since "2 weeks ago"
```

Show only the top five contributors and files:

```bash
gitscope analyze . --top 5
```

Save the analysis as JSON:

```bash
gitscope analyze . --export reports\summary.json
```

## Run tests

Run all tests with:

```bash
pytest -v
```

## Example commands

Show help:

```bash
gitscope --help
```

Show the version:

```bash
gitscope --version
```
