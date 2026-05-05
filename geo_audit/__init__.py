"""geo-audit — open-source GEO audit toolkit.

Score any URL for AI search visibility (ChatGPT, Perplexity, Claude,
Google AI Overviews, Bing Copilot, Yandex Neuro) and produce a prioritized
action plan.

License: MIT
Repository: https://github.com/g-shevchenko/geo-audit
"""

__version__ = "0.2.0"
__methodology_version__ = "1"

from geo_audit.modules.base import ModuleArgs, ModuleResult, Finding

__all__ = ["__version__", "__methodology_version__", "ModuleArgs", "ModuleResult", "Finding"]
