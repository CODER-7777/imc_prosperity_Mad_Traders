# Manual Trading Strategy (Round 1 — Exchange Auction)

This document contains the optimal order parameters for the manual trading challenge "An Intarian Welcome" based on a uniform clearing price auction analysis.

## ⚠️ Important Mechanics
It is critical to follow these exact volumes. The Exchange uses a **uniform clearing price auction**:
1. The exchange selects a *single* clearing price that maximizes traded volume.
2. Ties are broken by choosing the higher price.
3. Your orders are submitted last, meaning you have the **lowest time priority** at any price level.
4. **Volume precision is crucial.** Submitting volumes that are too high will push the clearing price aggressively against you, wiping out all potential profit.

---

## 🟢 DRYLAND FLAX
**Auto-sell Price:** 30 XiRECs (No trading fees)

| Parameter | Value |
| --- | --- |
| Action | **BUY** |
| Price | **30** |
| Volume | **9999** |

*Expected Profit: ~9,999 XiRECs*

**Why this works:**
- At volume 10,000, the clearing price jumps from 29 to 30, meaning you buy at 30 and auto-sell at 30 (0 profit).
- By capping the volume at **9,999**, the clearing price stays at 29. You purchase 9,999 units at 29 and the system auto-sells them at 30 for a profit of 1 per unit.

---

## 🟢 EMBER MUSHROOM
**Auto-sell Price:** 20 XiRECs (Trading fee: 0.10 XiRECs per unit traded)

| Parameter | Value |
| --- | --- |
| Action | **BUY** |
| Price | **17** |
| Volume | **19999** |

*Expected Profit: ~77,996 XiRECs*

**Why this works:**
- You want to acquire as much volume as possible while keeping the clearing price low.
- At volume 20,000, the clearing price jumps from 16 to 17, which reduces your per-unit profit by 1 full XiREC.
- By capping the volume at **19,999**, you force the clearing price to settle at 16 (where existing bids consume 71k out of 91k supply, leaving perfectly enough room for your 19,999 units).
- Profit math: Auto-sell (20) - Clearing Price (16) - Fees (2 * 0.10) = 3.80 per unit. (3.80 × 19,999 ≈ 76,000 to 78,000 profit).

---

### 💰 Total Expected Manual Profit: **~88,000 XiRECs**
