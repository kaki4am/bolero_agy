Tuner degradation live-trading pause was rejected as the tuner currently safely discards negative configs without needing to halt the active stable strategy.
Rejected Trade Ideas (Time-of-day, Day-of-week, Pair Exclusions) because they were highly overfit to historical data and directly caused the reported trade stagnation.
Rejected Time-of-Day, Day-of-Week, and Pair Exclusion filters due to high risk of curve-fitting and degrading overall system adaptability.
Static time-of-day, day-of-week, and pair-specific exclusions were rejected in V150 to avoid curve-fitting, moving instead to dynamic volatility and momentum filters.
Rejected static time-of-day, day-of-week, and static pair exclusions (HFTUSDT, SYNUSDT, etc.) to avoid curve-fitting and over-optimization as per committee advice.
Time-of-Day, Day-of-Week, and Pair Exclusions were explicitly rejected by the committee to avoid curve-fitting and trade stagnation.
- Rejected static time-of-day, day-of-week, and static pair exclusions as they presented high overfitting risk; we opted for dynamic volatility checks instead.
Time-of-Day, Day-of-Week, and Pair exclusions were rejected to avoid curve-fitting, prioritizing dynamic volatility checks instead.
