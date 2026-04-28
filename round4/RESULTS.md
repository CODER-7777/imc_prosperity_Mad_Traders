# Round 4 Results

## Strategy: `strategy.py` (V6 -- No VF Trading)

### Core Approach
Black-Scholes option arbitrage. Price 10 VEV call option strikes using the BS model,
sweep all mispriced orders from the order book, and place full position-limit passive
quotes at +/-1 tick from theoretical fair value.

### Products Traded

| Product | Strategy | Position Limit | PnL |
|---|---|---|---:|
| HYDROGEL_PACK | EMA market-making + Mark 38 fade | 200 | +2,075 |
| VELVETFRUIT_EXTRACT | EMA tracking only (no active trading) | 200 | 0 |
| VEV_4000 | BS fair-value + full capacity quotes | 300 | +8,894 |
| VEV_4500 | BS fair-value + full capacity quotes | 300 | +9,876 |
| VEV_5000 | BS fair-value + full capacity quotes | 300 | +8,972 |
| VEV_5100 | BS fair-value + full capacity quotes | 300 | +10,606 |
| VEV_5200 | BS fair-value + full capacity quotes | 300 | +8,866 |
| VEV_5300 | BS fair-value + full capacity quotes | 300 | +5,412 |
| VEV_5400 | BS fair-value + full capacity quotes | 300 | +2,384 |
| VEV_5500 | BS fair-value + full capacity quotes | 300 | +831 |
| VEV_6000 | BS fair-value (no fills -- too far OTM) | 300 | 0 |
| VEV_6500 | BS fair-value (no fills -- too far OTM) | 300 | 0 |

### Key Parameters
- sigma (implied vol): 0.17 annualized (calibrated from historical data)
- TTE: 4 days, calculated as `VEV_TTE_START - (day - 1) - ts/1M`
- EMA alpha: 0.08 (HP and VF fair value tracking)
- VEV edge: +/-1 tick (aggressive/passive threshold)
- HP spread: +/-4 ticks with Mark 38 counterparty fade

### Counterparty Intelligence

| Counterparty | Product | Behavior | Our Response |
|---|---|---|---|
| Mark 38 | HYDROGEL_PACK | Buys high, sells low | Fade (trade opposite) |
| Mark 22 | VEV_* | Consistent option seller | Front-run predictable flow |
| Mark 55 | VELVETFRUIT_EXTRACT | Mean-reverts around 5248 | No active trading (drag) |

### Mechanics
- Black-Scholes call pricing for 10 option voucher strikes
- `math.erf()` based normal CDF (no scipy dependency)
- Full position-limit passive quoting on VEV order books
- `jsonpickle` state persistence for EMA + day tracking
- Counterparty trade tape analysis via `market_trades`

### Result
**Best PnL: 57,916** (Submission 539034)

### Version Evolution

See [`versions/VERSION_LOG.md`](versions/VERSION_LOG.md) for detailed iteration history.

| Version | PnL | Key Change |
|---|---:|---|
| V1 | 22,568 | Baseline with dynamic vol + delta hedging |
| V2 | 3,429 | Conservative -- regression |
| V3 | 47,230 | Full capacity VEV quotes -- breakthrough |
| V4 | 45,566 | Over-engineered counterparty -- slight regression |
| **V6** | **57,916** | **Stopped VF trading -- eliminated 10.7k drag** |

### Lessons Learned
- Simplicity wins: V3 (271 lines, 47k PnL) beat V1 (512 lines, 22.5k PnL)
- Full capacity passive quotes was the single biggest improvement (+24k PnL)
- Delta hedging is a net drag -- the hedge cost (-10.7k) exceeds the benefit
- Not all counterparty signals help -- Mark 38 alone optimal; adding Mark 14 hurt
- Static sigma (0.17) outperformed dynamic realized volatility estimation
- Not trading VF at all saved 10,686 in losses
