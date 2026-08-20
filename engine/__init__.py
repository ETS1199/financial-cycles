"""AM Overheating Index engine for Canada (and other Advanced Markets).

Replicates the Advanced-Market track of Chen & Svirydzenka (2021), IMF WP/21/116.
See CALCULATIONS.md for the step-by-step method this package implements.

Pipeline (module -> CALCULATIONS.md steps):
    config   configuration (method + country)      Extensibility / architecture
    data     load, CPI-align, deflate, log         Steps 1-3
    filters  CF band-pass: two-sided & one-sided    Steps 4-5
    index    gaps, flags, Overheating Index          Steps 6-8
    dating   Harding-Pagan turning points            validation only
    crosscheck  GDP gap vs external output gap        validation only (Phase 3)
    run      orchestrator: run(country, method)
"""
__all__ = ["config", "data", "filters", "index", "dating", "crosscheck", "run"]
