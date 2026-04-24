# Round 2 Results

## Strategy: `v4_round_2_strategy.py`

### Products Traded
| Product | Strategy | Position Limit |
|---|---|---|
| ASH_COATED_OSMIUM | Mean-reversion around FV=10000, inventory-skewed market making | 80 |
| INTARIAN_PEPPER_ROOT | Max long trend-following (+1000/day drift) | 80 |

### New Mechanics
- **Market Access Fee (MAF)**: Bid 1500 XIREC for priority market access (top 50% → 25% extra order volume)

### Key Decisions
- Carried forward the proven R1 core logic
- Added `bid()` method for MAF mechanic
- Conservative MAF bid of 1500 to ensure positive EV

### Result
✅ **Qualified for Round 3**

### Lessons Learned
- The R1 strategy core is robust — don't fix what isn't broken
- MAF is a strategic decision: bid enough to get priority, but not so much it eats profits
