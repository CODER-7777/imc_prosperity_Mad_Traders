IMC Prosperity Round 3 Strategy Versions
========================================

v2_plus_991.py
--------------
This is the script from submission 385148 that achieved +991 PnL. 
- It accidentally bypassed position limit rejections on the sell side, which prevented it from market-making aggressively and taking losses. 
- It lacked the theta exit strategy for options.

v3_minus_68k.py
---------------
This is the script from submission 400606/386200 that crashed to -68,000 PnL.
- It introduced the mathematically perfect `OrderManager` which prevented all rejections.
- Because orders were no longer rejected, it fed liquidity directly to smarter bots in the Delta-1 market, resulting in massive adverse selection losses.
- It also contained a 365.0 day-count convention bug in the Black-Scholes formula.

v4_god_mode.py
--------------
This is the latest optimized script (currently active as `strategy.py`).
- Delta-1 market-making is COMPLETELY DISABLED to prevent the -68k losses.
- The Black-Scholes formula is fixed to use 252 trading days, increasing option valuations by ~30%.
- Velvetfruit Extract is used purely as a taker-only delta hedge for the options portfolio.

If you ever want to revert to the +991 strategy, simply copy the contents of `v2_plus_991.py` into `strategy.py`!
