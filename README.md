# IMC Prosperity 4 - Mad Traders

Algorithmic trading competition by IMC Trading (2025)
Team: Mad_Traders | Language: Python 3.12 | Platform: IMC Prosperity Sandbox

---

## Competition Results

| Round | PnL | Strategy | Key Products | Status |
|:-----:|----:|----------|:-------------|:------:|
| R2 | Qualified | Mean-reversion + Trend-following | Osmium, Pepper Root | Passed |
| R3 | Qualified | Options market-making (IV smile) | + Volcanic Rock Vouchers | Passed |
| R4 | 57,916 | BS option arbitrage + counterparty fade | + HYDROGEL, VEV options | Best |
| R5 | -- | In progress | -- | Pending |

---

## Technical Highlights

### Black-Scholes Option Arbitrage (Round 4)
Priced 10 VEV call option strikes using Black-Scholes model, swept all mispriced orders from the order book, and placed full position-limit passive quotes at +/-1 tick from theoretical fair value, achieving 57,916 PnL across 4 simulated trading days.

### Counterparty Intelligence
Analyzed historical trade tapes to classify counterparty behavior:
- Market makers (Mark 22): Predictable option sellers - front-run their flow
- Bad traders (Mark 38): Consistently buy high - fade their trades
- Informed traders (Mark 67): Accurate directional bets - follow their signals

### Core Algorithms

| Algorithm | Application | Implementation |
|-----------|------------|----------------|
| Black-Scholes pricing | VEV option fair value | math.erf() CDF, no scipy |
| EMA tracking | HP/VF fair value estimation | alpha=0.08, persistent state |
| Order book sweep | Aggressive mispricing capture | Multi-level ask/bid sweep |
| Counterparty fading | HP market-making edge | Mark 38 trade tape analysis |
| Inventory skew | Risk management | Position-proportional quote bias |

---

## Repository Structure

The main branch contains only the final strategies and core tools. Trial algorithms, experiments, and backtesting variations are maintained in their respective branch names (e.g., `round4/trials`).

- `round2/` : Round 2 final strategy (Mean-reversion + trend-following)
- `round3/` : Round 3 final strategy (Options MM with IV smile tracking)
- `round4/` : Round 4 final strategy (BS option arbitrage)
- `round5/` : Round 5 ongoing strategy
- `tools/` : Internal tools and data modeling classes
- `backtester/` : Custom offline backtesting engine

---

## Backtester Credits

This repository utilizes a custom Python-based offline backtester located in the `backtester/` directory.

Acknowledgements:
- Based significantly on the open-source backtester by **jmerle** (imc-prosperity-3-backtester).
- Incorporates logging integrations compatible with visualizer tools by **kevin-fu1**.

---

## Methodology

1. Data Analysis: Parse historical CSVs to identify product mechanics and price patterns.
2. Counterparty Profiling: Classify traders by behavior (market makers, informed, noise).
3. Strategy Development: Implement pricing models (EMA, BS) and order execution logic.
4. Backtesting: Run against historical data and submit to IMC sandbox, analyzing PnL logs per product.
5. Iteration: Version, compare, identify regressions, and converge on optimal parameters.

### Design Decisions
- No external libraries: Pure Python (math, json, jsonpickle). No numpy or scipy.
- State persistence: EMA values and day counters serialized via jsonpickle.
- Position management: Full limit utilization with inventory skew for risk control.
- Execution budget: All strategies designed to complete within the 900ms per tick restriction.
