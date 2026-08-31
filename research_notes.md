Tuner degradation live-trading pause was rejected as the tuner currently safely discards negative configs without needing to halt the active stable strategy.
Rejected Trade Ideas (Time-of-day, Day-of-week, Pair Exclusions) because they were highly overfit to historical data and directly caused the reported trade stagnation.
Rejected Time-of-Day, Day-of-Week, and Pair Exclusion filters due to high risk of curve-fitting and degrading overall system adaptability.
Static time-of-day, day-of-week, and pair-specific exclusions were rejected in V150 to avoid curve-fitting, moving instead to dynamic volatility and momentum filters.
