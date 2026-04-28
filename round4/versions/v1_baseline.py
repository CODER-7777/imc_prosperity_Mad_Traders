"""
Round 4 Trader — IMC Prosperity
================================
Products: HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VELVETFRUIT_EXTRACT_VOUCHER (VEV_*)

Counterparty intelligence (from historical data analysis):
──────────────────────────────────────────────────────────
Mark 22  → Consistent market-maker / option seller.  Always selling VEVs to
            Mark 01 / Mark 14. Sells HYDROGEL at the ask and buys at the bid.
            We front-run Mark 22's predictable order-book activity.

Mark 38  → Aggressive buyer of HYDROGEL at or above mid; average buy price
            ~10000.  We sell into Mark 38 when he appears on the tape.

Mark 14  → Frequent two-sided HYDROGEL trader; buys below mid (~9988).
            We trade in the opposite direction: buy when Mark 14 is selling.

Mark 01  → Buys OTM VEVs (5200-5500) from Mark 22 at slightly below Mark 22's
            ask.  Signals that those vouchers have value — follow along.

Mark 55  → Buys AND sells VELVETFRUIT in roughly equal volume, mean-reverts
            around ~5248.  Acts as a noisy spread-trader. We fade Mark 55's
            aggressive moves.

Mark 67  → Buys VELVETFRUIT only; average price ~5249.  Informed buyer —
            buying alongside him when price is depressed is profitable.

Strategy per product
────────────────────
HYDROGEL_PACK:
  - Maintain a simple market-making spread of ±8 around a dynamic fair-value
    estimate (EMA of mid-price).
  - When the last trade was Mark 38 buying (at or above mid), lean short:
    place a bigger ask and tighten the bid.
  - When the last trade was Mark 14 selling (below mid), lean long.
  - Max position: ±175 (keep 25 units as buffer).

VELVETFRUIT_EXTRACT:
  - Mean-reversion market-maker around EMA(mid).
  - When Mark 67 is on the tape as buyer, increase buy-side aggression.
  - When Mark 55 was the last buyer (price often elevated), lean short.
  - Max position: ±175.

VELVETFRUIT_EXTRACT_VOUCHER (VEV_*):
  - Each VEV_<K> is a call option on VELVETFRUIT_EXTRACT with strike K.
  - Mark 22 is the dominant seller; Mark 01 follows fair value.
  - Strategy: When the best ask for a VEV is below our Black-Scholes estimate
    (using realized vol of VF), BUY up to position limit (300).
  - When best bid is above our BS estimate, SELL (short up to −300).
  - Hedge VEV exposure via VELVETFRUIT_EXTRACT position (delta hedge).

All sizing obeys position limits with a safety buffer.
"""

from datamodel import (
    OrderDepth, TradingState, Order, Trade,
    Symbol, Product, Position, Listing, Observation
)
from typing import Dict, List, Optional, Tuple
import math
import json


# ─── Constants ────────────────────────────────────────────────────────────────

PRODUCTS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"]
VEV_STRIKES = [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]
VEV_SYMBOLS = [f"VEV_{k}" for k in VEV_STRIKES]

POSITION_LIMITS = {
    "HYDROGEL_PACK":          200,
    "VELVETFRUIT_EXTRACT":    200,
    **{f"VEV_{k}": 300 for k in VEV_STRIKES},
}

# Safety buffer — never use the last N units
BUFFER = 25

# EMA decay (per timestamp tick)
EMA_ALPHA = 0.10

# Market-making half-spread (in price units)
HP_HALF_SPREAD   = 8     # HYDROGEL
VF_HALF_SPREAD   = 3     # VELVETFRUIT
VEV_EDGE         = 3     # VEV edge above/below BS price

# Realized vol for VEV Black-Scholes (annualised, computed from historical data)
# VF std ≈ 18 over ~30 000 ticks; 1 day = 10 000 ticks → ~30 ticks window used
# Approximate annualised vol: std(mid)/mean(mid) * sqrt(252)
VF_REALIZED_VOL  = 0.055   # ~5.5% annualised — will be updated in-state

# Trading days remaining for VEVs in Round 4 (TTE = 4 days → ~4/252 years)
# VEVs expire after round, so TTE ≈ 4 trading days → (updated each step)
VEV_DAYS_TOTAL   = 4
STEPS_PER_DAY    = 1000   # approximate steps per in-game day
STEPS_PER_YEAR   = 252 * STEPS_PER_DAY


# ─── Utilities ────────────────────────────────────────────────────────────────

def black_scholes_call(S: float, K: float, T: float, sigma: float) -> float:
    """Black-Scholes call price (risk-neutral drift = 0)."""
    if T <= 0 or S <= 0:
        return max(S - K, 0.0)
    d1 = (math.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * _norm_cdf(d1) - K * _norm_cdf(d2)


def bs_call_delta(S: float, K: float, T: float, sigma: float) -> float:
    """Delta of a BS call."""
    if T <= 0 or S <= 0:
        return 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + 0.5 * sigma ** 2 * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d1)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def mid_price(od: OrderDepth) -> Optional[float]:
    if od.buy_orders and od.sell_orders:
        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        return (best_bid + best_ask) / 2
    if od.buy_orders:
        return max(od.buy_orders)
    if od.sell_orders:
        return min(od.sell_orders)
    return None


def best_bid(od: OrderDepth) -> Optional[int]:
    return max(od.buy_orders) if od.buy_orders else None


def best_ask(od: OrderDepth) -> Optional[int]:
    return min(od.sell_orders) if od.sell_orders else None


def available_buy(product: str, position: int) -> int:
    """How many more units we can buy."""
    limit = POSITION_LIMITS[product] - BUFFER
    return max(0, limit - position)


def available_sell(product: str, position: int) -> int:
    """How many more units we can sell (short)."""
    limit = POSITION_LIMITS[product] - BUFFER
    return max(0, limit + position)


# ─── State (persisted in traderData JSON) ─────────────────────────────────────

DEFAULT_STATE = {
    "ema": {},          # product → float
    "vol_sq_sum": 0.0,  # for VF realized vol
    "vol_n": 0,
    "vf_sigma": VF_REALIZED_VOL,
    "last_buyer": {},   # product → buyer str
    "last_seller": {},  # product → seller str
    "prev_mid": {},     # product → float
    "timestamp": 0,
}


def load_state(raw: str) -> dict:
    if not raw:
        return DEFAULT_STATE.copy()
    try:
        return json.loads(raw)
    except Exception:
        return DEFAULT_STATE.copy()


class _NumpySafeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return int(obj)
        except (TypeError, ValueError):
            pass
        try:
            return float(obj)
        except (TypeError, ValueError):
            pass
        return super().default(obj)


def save_state(state: dict) -> str:
    return json.dumps(state, cls=_NumpySafeEncoder)


# ─── Main Trader ──────────────────────────────────────────────────────────────

class Trader:

    def run(self, trading_state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        state = load_state(trading_state.traderData)
        orders: Dict[str, List[Order]] = {}

        positions: Dict[str, int] = trading_state.position or {}

        # ── 1. Update counterparty intel from last-tick trades ──────────────
        for symbol, trades in trading_state.market_trades.items():
            for t in trades:
                if t.buyer:
                    state["last_buyer"][symbol] = t.buyer
                if t.seller:
                    state["last_seller"][symbol] = t.seller

        # ── 2. Update EMAs & realized vol ───────────────────────────────────
        for product in PRODUCTS + VEV_SYMBOLS:
            if product not in trading_state.order_depths:
                continue
            od = trading_state.order_depths[product]
            mp = mid_price(od)
            if mp is None:
                continue

            prev_ema = state["ema"].get(product, mp)
            state["ema"][product] = EMA_ALPHA * mp + (1 - EMA_ALPHA) * prev_ema

            # Realized vol update for VF
            if product == "VELVETFRUIT_EXTRACT":
                prev_mid = state["prev_mid"].get(product)
                if prev_mid and prev_mid > 0:
                    ret_sq = (mp / prev_mid - 1) ** 2
                    state["vol_sq_sum"] += ret_sq
                    state["vol_n"] += 1
                    if state["vol_n"] > 10:
                        # annualise: steps per year = 252 * 1000
                        raw_var = state["vol_sq_sum"] / state["vol_n"]
                        state["vf_sigma"] = math.sqrt(raw_var * STEPS_PER_YEAR)
                state["prev_mid"][product] = mp

        sigma = max(0.01, state["vf_sigma"])

        # ── 3. Compute VEV time-to-expiry (TTE in years) ────────────────────
        # timestamp increases by 100 each step; day switches every 10 000 ticks
        ts = trading_state.timestamp
        # Steps elapsed in round
        steps_elapsed = ts  # timestamp resets each day — handle via day
        day = getattr(trading_state, 'day', 1)  # day attribute if available
        total_steps_elapsed = (day - 1) * STEPS_PER_DAY + ts / 100
        total_steps_remaining = max(1, VEV_DAYS_TOTAL * STEPS_PER_DAY - total_steps_elapsed)
        T_years = total_steps_remaining / STEPS_PER_YEAR

        # ── 4. Trade HYDROGEL_PACK ───────────────────────────────────────────
        if "HYDROGEL_PACK" in trading_state.order_depths:
            orders["HYDROGEL_PACK"] = self._trade_hydrogel(
                trading_state.order_depths["HYDROGEL_PACK"],
                positions.get("HYDROGEL_PACK", 0),
                state,
            )

        # ── 5. Trade VELVETFRUIT_EXTRACT ─────────────────────────────────────
        if "VELVETFRUIT_EXTRACT" in trading_state.order_depths:
            orders["VELVETFRUIT_EXTRACT"] = self._trade_velvetfruit(
                trading_state.order_depths["VELVETFRUIT_EXTRACT"],
                positions.get("VELVETFRUIT_EXTRACT", 0),
                state,
            )

        # ── 6. Trade VEV vouchers ────────────────────────────────────────────
        vf_mid = state["ema"].get("VELVETFRUIT_EXTRACT", 5248.0)
        vev_orders, vev_delta = self._trade_vevs(
            trading_state.order_depths,
            positions,
            vf_mid,
            sigma,
            T_years,
            state,
        )
        orders.update(vev_orders)

        # ── 7. Delta-hedge VEV exposure via VELVETFRUIT_EXTRACT ──────────────
        vev_hedge = self._delta_hedge_vev(
            vev_delta,
            trading_state.order_depths.get("VELVETFRUIT_EXTRACT"),
            positions.get("VELVETFRUIT_EXTRACT", 0),
            orders.get("VELVETFRUIT_EXTRACT", []),
        )
        if vev_hedge:
            # Merge with existing VF orders
            orders["VELVETFRUIT_EXTRACT"] = (
                orders.get("VELVETFRUIT_EXTRACT", []) + vev_hedge
            )

        state["timestamp"] = ts
        return orders, 0, save_state(state)

    # ── HYDROGEL_PACK ─────────────────────────────────────────────────────────

    def _trade_hydrogel(
        self,
        od: OrderDepth,
        position: int,
        state: dict,
    ) -> List[Order]:
        orders = []
        fair = state["ema"].get("HYDROGEL_PACK", 9994.0)
        mp = mid_price(od)
        if mp:
            fair = state["ema"].get("HYDROGEL_PACK", mp)

        last_buyer  = state["last_buyer"].get("HYDROGEL_PACK", "")
        last_seller = state["last_seller"].get("HYDROGEL_PACK", "")

        # Bias: Mark 38 aggressively buys → expect price high → lean short
        #       Mark 14 selling → lean long
        bias = 0
        if last_buyer == "Mark 38":
            bias = +3   # shift fair value up so our ask becomes more attractive
        elif last_seller == "Mark 14":
            bias = -3   # shift fair value down → tighten bid

        fair_adj = fair + bias

        # Aggressive take: lift cheap asks / hit rich bids first
        if od.sell_orders:
            for ask_price in sorted(od.sell_orders):
                if ask_price < fair_adj - HP_HALF_SPREAD:
                    vol = min(-od.sell_orders[ask_price], available_buy("HYDROGEL_PACK", position))
                    if vol > 0:
                        orders.append(Order("HYDROGEL_PACK", ask_price, vol))
                        position += vol

        if od.buy_orders:
            for bid_price in sorted(od.buy_orders, reverse=True):
                if bid_price > fair_adj + HP_HALF_SPREAD:
                    vol = min(od.buy_orders[bid_price], available_sell("HYDROGEL_PACK", position))
                    if vol > 0:
                        orders.append(Order("HYDROGEL_PACK", bid_price, -vol))
                        position -= vol

        # Passive quotes
        our_bid = int(fair_adj - HP_HALF_SPREAD)
        our_ask = int(fair_adj + HP_HALF_SPREAD)

        buy_qty  = min(20, available_buy("HYDROGEL_PACK", position))
        sell_qty = min(20, available_sell("HYDROGEL_PACK", position))

        if buy_qty > 0:
            orders.append(Order("HYDROGEL_PACK", our_bid, buy_qty))
        if sell_qty > 0:
            orders.append(Order("HYDROGEL_PACK", our_ask, -sell_qty))

        return orders

    # ── VELVETFRUIT_EXTRACT ───────────────────────────────────────────────────

    def _trade_velvetfruit(
        self,
        od: OrderDepth,
        position: int,
        state: dict,
    ) -> List[Order]:
        orders = []
        fair = state["ema"].get("VELVETFRUIT_EXTRACT", 5248.0)

        last_buyer  = state["last_buyer"].get("VELVETFRUIT_EXTRACT", "")
        last_seller = state["last_seller"].get("VELVETFRUIT_EXTRACT", "")

        # Mark 67 buying → informed demand → follow
        # Mark 55 just bought → noisy / mean-reverting → fade slightly
        bias = 0
        if last_buyer == "Mark 67":
            bias = +1
        elif last_buyer == "Mark 55":
            bias = -1
        elif last_seller == "Mark 55":
            bias = +1

        fair_adj = fair + bias

        # Aggressive take
        if od.sell_orders:
            for ask_price in sorted(od.sell_orders):
                if ask_price < fair_adj - VF_HALF_SPREAD:
                    vol = min(-od.sell_orders[ask_price], available_buy("VELVETFRUIT_EXTRACT", position))
                    if vol > 0:
                        orders.append(Order("VELVETFRUIT_EXTRACT", ask_price, vol))
                        position += vol

        if od.buy_orders:
            for bid_price in sorted(od.buy_orders, reverse=True):
                if bid_price > fair_adj + VF_HALF_SPREAD:
                    vol = min(od.buy_orders[bid_price], available_sell("VELVETFRUIT_EXTRACT", position))
                    if vol > 0:
                        orders.append(Order("VELVETFRUIT_EXTRACT", bid_price, -vol))
                        position -= vol

        # Passive quotes
        our_bid = int(fair_adj - VF_HALF_SPREAD)
        our_ask = int(fair_adj + VF_HALF_SPREAD)

        buy_qty  = min(15, available_buy("VELVETFRUIT_EXTRACT", position))
        sell_qty = min(15, available_sell("VELVETFRUIT_EXTRACT", position))

        if buy_qty > 0:
            orders.append(Order("VELVETFRUIT_EXTRACT", our_bid, buy_qty))
        if sell_qty > 0:
            orders.append(Order("VELVETFRUIT_EXTRACT", our_ask, -sell_qty))

        return orders

    # ── VEV Vouchers ──────────────────────────────────────────────────────────

    def _trade_vevs(
        self,
        order_depths: Dict[str, OrderDepth],
        positions: Dict[str, int],
        vf_mid: float,
        sigma: float,
        T_years: float,
        state: dict,
    ) -> Tuple[Dict[str, List[Order]], float]:
        """
        Trade all VEV vouchers vs Black-Scholes theoretical value.
        Returns orders dict and total delta exposure (positive = long VF equivalent).
        """
        all_orders: Dict[str, List[Order]] = {}
        total_delta = 0.0

        for K in VEV_STRIKES:
            sym = f"VEV_{K}"
            if sym not in order_depths:
                continue

            od     = order_depths[sym]
            pos    = positions.get(sym, 0)
            theory = black_scholes_call(vf_mid, K, T_years, sigma)
            delta  = bs_call_delta(vf_mid, K, T_years, sigma)

            vev_orders = []

            # Buy if market is cheap vs theory
            ba = best_ask(od)
            if ba is not None and ba < theory - VEV_EDGE:
                qty = min(
                    -od.sell_orders.get(ba, 0),  # available at that level
                    available_buy(sym, pos),
                    10,  # don't slam the whole book at once
                )
                if qty > 0:
                    vev_orders.append(Order(sym, ba, qty))
                    total_delta += qty * delta
                    pos += qty

            # Sell if market is rich vs theory
            bb = best_bid(od)
            if bb is not None and bb > theory + VEV_EDGE:
                qty = min(
                    od.buy_orders.get(bb, 0),
                    available_sell(sym, pos),
                    10,
                )
                if qty > 0:
                    vev_orders.append(Order(sym, bb, -qty))
                    total_delta -= qty * delta
                    pos -= qty

            if vev_orders:
                all_orders[sym] = vev_orders

        return all_orders, total_delta

    # ── Delta Hedge ───────────────────────────────────────────────────────────

    def _delta_hedge_vev(
        self,
        vev_delta: float,
        od: Optional[OrderDepth],
        vf_position: int,
        existing_vf_orders: List[Order],
    ) -> List[Order]:
        """
        Hedge the VEV delta exposure by trading VELVETFRUIT_EXTRACT.
        vev_delta > 0 → we are long delta → sell VF to hedge.
        """
        if od is None or abs(vev_delta) < 1:
            return []

        # Account for VF orders already placed
        pending_vf = sum(o.quantity for o in existing_vf_orders)
        net_vf_pos = vf_position + pending_vf

        # Target: net_vf_pos + hedge = -vev_delta (to flatten)
        hedge_qty = int(round(-vev_delta - net_vf_pos))
        if hedge_qty == 0:
            return []

        orders = []
        if hedge_qty > 0:
            # Need to buy VF
            hedge_qty = min(hedge_qty, available_buy("VELVETFRUIT_EXTRACT", net_vf_pos))
            if od.sell_orders and hedge_qty > 0:
                ba = min(od.sell_orders)
                orders.append(Order("VELVETFRUIT_EXTRACT", ba, hedge_qty))
        else:
            # Need to sell VF
            hedge_qty = min(-hedge_qty, available_sell("VELVETFRUIT_EXTRACT", net_vf_pos))
            if od.buy_orders and hedge_qty > 0:
                bb = max(od.buy_orders)
                orders.append(Order("VELVETFRUIT_EXTRACT", bb, -hedge_qty))

        return orders