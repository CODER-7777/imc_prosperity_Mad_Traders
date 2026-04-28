# IMC Prosperity 4 -- Mad Traders

> Algorithmic trading competition by IMC Trading (2025)
> **Team:** Mad_Traders | **Language:** Python 3.12 | **Platform:** IMC Prosperity Sandbox

---

## Competition Results

| Round | PnL | Strategy | Key Products | Status |
|:-----:|----:|----------|:-------------|:------:|
| R2 | Qualified | Mean-reversion + Trend-following | Osmium, Pepper Root | Passed |
| R3 | Qualified | Options market-making (IV smile) | + Volcanic Rock Vouchers | Passed |
| R4 | **57,916** | **BS option arbitrage + counterparty fade** | + HYDROGEL, VEV options | Best |
| R5 | -- | In progress | -- | Pending |

---

## Technical Highlights

### Black-Scholes Option Arbitrage (Round 4)
Priced 10 VEV call option strikes using Black-Scholes model, swept all mispriced orders
from the order book, and placed full position-limit passive quotes at +/-1 tick from
theoretical fair value -- achieving **57,916 PnL** across 4 simulated trading days.

### Counterparty Intelligence
Analyzed historical trade tapes to classify counterparty behavior:
- **Market makers** (Mark 22): Predictable option sellers -- front-run their flow
- **Bad traders** (Mark 38): Consistently buy high -- fade their trades
- **Informed traders** (Mark 67): Accurate directional bets -- follow their signals

### Strategy Evolution (Round 4)
Iterated through 6 strategy versions, using rigorous log analysis to identify
what worked and what didn't:

```
V1 (22.5k) -> V2 (3.4k) -> V3 (47.2k) -> V4 (45.6k) -> V6 (57.9k)
               regression     breakthrough   over-engineered   optimal
```

Key insight: simplicity wins. The 224-line V6 outperformed the 512-line V1 by 2.5x.

### Core Algorithms

| Algorithm | Application | Implementation |
|-----------|------------|----------------|
| Black-Scholes pricing | VEV option fair value | `math.erf()` CDF, no scipy |
| EMA tracking | HP/VF fair value estimation | alpha=0.08, persistent state |
| Order book sweep | Aggressive mispricing capture | Multi-level ask/bid sweep |
| Counterparty fading | HP market-making edge | Mark 38 trade tape analysis |
| Inventory skew | Risk management | Position-proportional quote bias |

---

## Repository Structure

```
imc_prosperity_Mad_Traders/
├── round2/
│   ├── strategy.py              # Mean-reversion + trend-following
│   ├── data/                    # Market data CSVs
│   ├── docs/                    # Round documentation
│   └── RESULTS.md               # Performance summary
├── round3/
│   ├── strategy.py              # Options MM with IV smile tracking
│   ├── versions/                # Strategy iterations
│   ├── data/ & docs/
│   └── RESULTS.md
├── round4/
│   ├── strategy.py              # BS option arbitrage (best: 57.9k PnL)
│   ├── versions/                # V1-V6 with VERSION_LOG.md
│   │   ├── VERSION_LOG.md       # Detailed iteration history with PnL
│   │   ├── v1_baseline.py       # 22.5k -- dynamic vol, delta hedge
│   │   ├── v3_aggressive.py     # 47.2k -- full capacity quotes
│   │   └── v6_no_vf_trading.py  # 57.9k -- eliminated VF drag (best)
│   ├── data/ & docs/
│   └── RESULTS.md               # Round 4 performance breakdown
├── round5/
│   ├── strategy.py              # In progress
│   └── RESULTS.md
├── tools/
│   └── datamodel.py             # IMC platform data model
├── .gitignore
└── README.md
```

---

## Methodology

### Per-Round Workflow
1. **Data Analysis** -- Parse historical CSVs to identify product mechanics and price patterns
2. **Counterparty Profiling** -- Classify traders by behavior (market makers, informed, noise)
3. **Strategy Development** -- Implement pricing models (EMA, BS) and order execution logic
4. **Backtesting** -- Submit to IMC sandbox, analyze PnL logs per product
5. **Iteration** -- Version, compare, identify regressions, and converge on optimal parameters

### Design Decisions
- No external libraries: Pure Python (`math`, `json`, `jsonpickle`) -- no numpy/scipy
- State persistence: EMA values and day counters serialized via `jsonpickle`
- Position management: Full limit utilization with inventory skew for risk control
- Execution budget: All strategies complete within 900ms per tick

---

## Setup

```bash
# Clone the repository
git clone https://github.com/CODER-7777/imc_prosperity_Mad_Traders.git
cd imc_prosperity_Mad_Traders

# View the winning Round 4 strategy
cat round4/strategy.py

# View version history and iteration analysis
cat round4/versions/VERSION_LOG.md
```

---

## Competition Format
- **Platform**: IMC Prosperity (https://prosperity.imc.com/) -- simulated exchange
- **Language**: Python 3.12 (restricted stdlib)
- **Execution**: `Trader.run()` called every tick with full order book and trade tape
- **Constraints**: Position limits per product, 900ms execution budget, 50KB state limit
