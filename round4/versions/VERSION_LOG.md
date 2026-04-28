# Round 4 -- Strategy Version Log

Tracking every iteration, what changed, and the PnL impact.

## Version History

| Version | File | Submission | PnL | Delta | Status |
|---------|------|-----------|----:|------:|--------|
| V1 | `v1_baseline.py` | `505741` | 22,568 | -- | Baseline |
| V2 | `v2_counterparty_intel.py` | `536828` | 3,429 | -19,139 | Regression |
| V3 | `v3_aggressive_sweep.py` | `537998` | 47,230 | +43,801 | Breakthrough |
| V4 | `v4_merged.py` | `538430` | 45,566 | -1,664 | Slight regression |
| V5 | `v5_ultra_final.py` | -- | -- | -- | Untested (draft) |
| **V6** | `v6_no_vf_trading.py` | `539034` | **57,916** | **+10,686** | **Best** |

---

## V1 -- Baseline (PnL: 22,568)
- Custom BS pricing, dynamic realized vol, counterparty bias, delta hedging
- Profit source: VEV_5100/5200/5300 = +23,182
- Drag: VF delta hedge cost = -3,705; HP market-making = -567

## V2 -- Counterparty Intel (PnL: 3,429)
- First attempt -- too conservative, no book sweep, high buffer (25)
- Failed because it didn't trade key VEVs (5000, 5200 = 0 PnL), lost on VEV_6000/6500 (-600)
- Lesson: Over-engineering doesn't beat simplicity

## V3 -- Aggressive Sweep (PnL: 47,230)
- Full position limit usage, sweep entire VEV book, static sigma=0.17, no delta hedge
- Key insight: Put ENTIRE remaining capacity as passive VEV quotes at +/-1 from BS fair
- Breakthrough: VEV_4000 went from -12 to +8,894; VEV_4500 from -12 to +9,876
- Profit source: VEVs = +55,845 gross, HP = +2,075, VF = -10,686 (hedge drag)

## V4 -- Merged (PnL: 45,566)
- V3 + added Mark 14 fading on HP + Mark 67 following on VF
- Regressed because Mark 14 logic over-traded HP (2,075 to 410, lost -1,664)
- Lesson: More counterparty signals != more profit. Mark 38-only was optimal.

## V5 -- Ultra Final (untested draft)
- Intermediate version combining V3 base with no-VF-trading hypothesis
- Superseded by V6 before submission

## V6 -- No VF Trading (PnL: 57,916) [BEST]
- V3 base + reverted HP to original Mark 38-only logic + stopped trading VF entirely
- VF was bleeding -10,686 in every backtest. Removing it saved that entire amount.
- Final breakdown: VEVs = +55,841 + HP = +2,075 + VF = 0 = 57,916

---

## Key Learnings

1. VEVs are the profit engine -- 96% of all profits come from BS-priced VEV options
2. Full capacity passive quotes was the single biggest improvement (V1 to V3: +24k)
3. Delta hedging is a net drag -- the VF hedge cost (-10.7k) exceeds the benefit
4. Simple beats complex -- V3 (271 lines, 47k) crushed V1 (512 lines, 22.5k)
5. Counterparty logic: less is more -- Mark 38 alone works; adding Mark 14/55/67 hurt
6. Static sigma (0.17) outperformed dynamic realized volatility estimation
7. Not trading a product can be more profitable than trading it badly

## PnL Breakdown (Best Run: V6 at 57,916)

```
VEV_5100                         +10,605.90
VEV_4500                          +9,875.77
VEV_5000                          +8,972.18
VEV_4000                          +8,893.78
VEV_5200                          +8,866.20
VEV_5300                          +5,411.96
VEV_5400                          +2,383.71
HYDROGEL_PACK                     +2,074.75
VEV_5500                            +831.45
VELVETFRUIT_EXTRACT                   +0.00
VEV_6000                              +0.00
VEV_6500                              +0.00
--------------------------------------------
TOTAL                            +57,915.69
```
