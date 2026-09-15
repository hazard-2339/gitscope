"""gitscope package."""

__version__ = "0.1.0"

try:
    from .analyzer import GitRepoAnalyzer
except ImportError:  # pragma: no cover - optional during early scaffolding
    GitRepoAnalyzer = None

__all__ = ["GitRepoAnalyzer", "__version__"]
