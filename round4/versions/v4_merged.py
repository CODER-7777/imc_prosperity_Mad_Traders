"""
Round 4 Trader — IMC Prosperity (V3 FINAL)
============================================
Merging 537998 (47k PnL) with our counterparty intelligence.

Key learnings from 537998:
  - Use FULL position limits (no buffer)
  - Put ENTIRE remaining capacity as passive VEV quotes at ±1 from BS fair
  - NO delta hedging (it's a net drag)
  - Simple, clean, fast

Our additions:
  - Counterparty biasing on HP (Mark 38) and VF (Mark 55/67)
  - Aggressive book sweep on all VEV levels
  - Inventory skew for risk management
"""

from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict, Any, Tuple
import jsonpickle
import math


class Trader:

    POS_LIMITS = {
        "HYDROGEL_PACK": 200,
        "VELVETFRUIT_EXTRACT": 200,
        **{f"VEV_{k}": 300 for k in [4000, 4500, 5000, 5100, 5200, 5300, 5400, 5500, 6000, 6500]}
    }

    VEV_STRIKES = {
        "VEV_4000": 4000, "VEV_4500": 4500, "VEV_5000": 5000,
        "VEV_5100": 5100, "VEV_5200": 5200, "VEV_5300": 5300,
        "VEV_5400": 5400, "VEV_5500": 5500, "VEV_6000": 6000, "VEV_6500": 6500
    }

    VEV_SIGMA = 0.17
    TRADING_DAYS = 252
    VEV_TTE_START = 4

    def norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def bs_call(self, S: float, K: float, T_days: float, sigma: float) -> float:
        """Black-Scholes call price. T_days in trading days."""
        T = T_days / self.TRADING_DAYS
        if T <= 0 or S <= 0:
            return max(0.0, S - K)
        sqrtT = math.sqrt(T)
        d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrtT)
        d2 = d1 - sigma * sqrtT
        return S * self.norm_cdf(d1) - K * self.norm_cdf(d2)

    def get_mid(self, od: OrderDepth):
        if not od.buy_orders or not od.sell_orders:
            return None
        return (max(od.buy_orders) + min(od.sell_orders)) / 2.0

    def bad_trader_net(self, product: str, market_trades, bad_name: str) -> int:
        """Net qty bought by bad trader (positive=bought, negative=sold)."""
        net = 0
        if product not in market_trades:
            return 0
        for t in market_trades[product]:
            if t.buyer == bad_name:
                net += t.quantity
            if t.seller == bad_name:
                net -= t.quantity
        return net

    def make_orders(self, product, od, fair, pos, limit, bid_skew=0, ask_skew=0,
                    spread=3, aggress_buy=None, aggress_sell=None):
        orders = []
        max_buy  = limit - pos
        max_sell = limit + pos

        # Aggressive orders first (take liquidity from bad traders)
        if aggress_buy and max_buy > 0:
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px <= aggress_buy and max_buy > 0:
                    qty = min(max_buy, -ask_vol)
                    orders.append(Order(product, ask_px, qty))
                    max_buy -= qty

        if aggress_sell and max_sell > 0:
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px >= aggress_sell and max_sell > 0:
                    qty = min(max_sell, bid_vol)
                    orders.append(Order(product, bid_px, -qty))
                    max_sell -= qty

        # Passive market-making with full remaining capacity
        our_bid = round(fair - spread + bid_skew)
        our_ask = round(fair + spread + ask_skew)

        if max_buy > 0:
            orders.append(Order(product, our_bid, max_buy))
        if max_sell > 0:
            orders.append(Order(product, our_ask, -max_sell))

        return orders

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        # ── Load persistent state ──────────────────────────────────────────────
        td = {}
        if state.traderData:
            try:
                td = jsonpickle.decode(state.traderData)
            except:
                td = {}

        alpha = 0.08
        hp_ema  = td.get("hp_ema",  10000.0)
        vf_ema  = td.get("vf_ema",  5247.0)
        day     = td.get("day", 1)
        prev_ts = td.get("prev_ts", -1)

        # Detect new day by timestamp reset
        if state.timestamp < prev_ts:
            day += 1
        prev_ts = state.timestamp

        # ── Update EMAs ───────────────────────────────────────────────────────
        if "HYDROGEL_PACK" in state.order_depths:
            mid = self.get_mid(state.order_depths["HYDROGEL_PACK"])
            if mid:
                hp_ema = alpha * mid + (1 - alpha) * hp_ema

        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            mid = self.get_mid(state.order_depths["VELVETFRUIT_EXTRACT"])
            if mid:
                vf_ema = alpha * mid + (1 - alpha) * vf_ema

        # ── VEV time to expiry ────────────────────────────────────────────────
        day_fraction = state.timestamp / 1_000_000
        tte_days = max(0.05, self.VEV_TTE_START - (day - 1) - day_fraction)

        # ═══════════════════════════════════════════════════════════════════════
        # 1. HYDROGEL_PACK — with counterparty intelligence
        # ═══════════════════════════════════════════════════════════════════════
        if "HYDROGEL_PACK" in state.order_depths:
            od   = state.order_depths["HYDROGEL_PACK"]
            pos  = state.position.get("HYDROGEL_PACK", 0)
            lim  = self.POS_LIMITS["HYDROGEL_PACK"]

            fair = hp_ema

            # Mark 38: bad trader who buys high / sells low — fade him
            net38 = self.bad_trader_net("HYDROGEL_PACK", state.market_trades, "Mark 38")
            # Mark 14: buys below mid — fade him too
            net14 = self.bad_trader_net("HYDROGEL_PACK", state.market_trades, "Mark 14")

            aggress_buy_px  = None
            aggress_sell_px = None
            bid_skew = 0
            ask_skew = 0

            if net38 < 0:
                aggress_buy_px = round(fair - 2)
                bid_skew = 3
            elif net38 > 0:
                aggress_sell_px = round(fair + 2)
                ask_skew = -3

            # Mark 14 bought below mid → mean revert, sell
            if net14 > 0:
                if aggress_sell_px is None:
                    aggress_sell_px = round(fair + 2)
                ask_skew = max(ask_skew, -2)
            elif net14 < 0:
                if aggress_buy_px is None:
                    aggress_buy_px = round(fair - 2)
                bid_skew = max(bid_skew, 2)

            # Inventory skew
            inv_skew = -int(pos * 0.05)
            bid_skew += inv_skew
            ask_skew += inv_skew

            orders = self.make_orders(
                "HYDROGEL_PACK", od, fair, pos, lim,
                bid_skew=bid_skew, ask_skew=ask_skew,
                spread=4,
                aggress_buy=aggress_buy_px,
                aggress_sell=aggress_sell_px
            )
            result["HYDROGEL_PACK"] = orders

        # ═══════════════════════════════════════════════════════════════════════
        # 2. VELVETFRUIT_EXTRACT — with counterparty intelligence
        # ═══════════════════════════════════════════════════════════════════════
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            od   = state.order_depths["VELVETFRUIT_EXTRACT"]
            pos  = state.position.get("VELVETFRUIT_EXTRACT", 0)
            lim  = self.POS_LIMITS["VELVETFRUIT_EXTRACT"]

            fair = vf_ema

            # Mark 55: bad trader on VF — fade
            net55 = self.bad_trader_net("VELVETFRUIT_EXTRACT", state.market_trades, "Mark 55")
            # Mark 67: informed buyer — follow
            net67 = self.bad_trader_net("VELVETFRUIT_EXTRACT", state.market_trades, "Mark 67")

            aggress_buy_px  = None
            aggress_sell_px = None
            bid_skew = 0
            ask_skew = 0

            if net55 < 0:
                aggress_buy_px = round(fair - 1)
                bid_skew = 2
            elif net55 > 0:
                aggress_sell_px = round(fair + 1)
                ask_skew = -2

            # Mark 67 is informed buyer — follow his direction
            if net67 > 0:
                if aggress_buy_px is None:
                    aggress_buy_px = round(fair - 1)
                bid_skew = max(bid_skew, 2)
            elif net67 < 0:
                if aggress_sell_px is None:
                    aggress_sell_px = round(fair + 1)
                ask_skew = min(ask_skew, -2)

            inv_skew = -int(pos * 0.03)
            bid_skew += inv_skew
            ask_skew += inv_skew

            orders = self.make_orders(
                "VELVETFRUIT_EXTRACT", od, fair, pos, lim,
                bid_skew=bid_skew, ask_skew=ask_skew,
                spread=2,
                aggress_buy=aggress_buy_px,
                aggress_sell=aggress_sell_px
            )
            result["VELVETFRUIT_EXTRACT"] = orders

        # ═══════════════════════════════════════════════════════════════════════
        # 3. VEV Options — BS pricing + FULL CAPACITY passive quotes
        # ═══════════════════════════════════════════════════════════════════════
        vf_price = vf_ema

        for vev, strike in self.VEV_STRIKES.items():
            if vev not in state.order_depths:
                continue

            od   = state.order_depths[vev]
            pos  = state.position.get(vev, 0)
            lim  = self.POS_LIMITS[vev]

            fair = self.bs_call(vf_price, strike, tte_days, self.VEV_SIGMA)

            orders = []
            max_buy  = lim - pos
            max_sell = lim + pos

            # Aggressive: sweep ALL underpriced asks
            for ask_px, ask_vol in sorted(od.sell_orders.items()):
                if ask_px < fair - 1 and max_buy > 0:
                    qty = min(max_buy, -ask_vol)
                    orders.append(Order(vev, ask_px, qty))
                    max_buy -= qty

            # Aggressive: hit ALL overpriced bids
            for bid_px, bid_vol in sorted(od.buy_orders.items(), reverse=True):
                if bid_px > fair + 1 and max_sell > 0:
                    qty = min(max_sell, bid_vol)
                    orders.append(Order(vev, bid_px, -qty))
                    max_sell -= qty

            # PASSIVE: put ENTIRE remaining capacity at ±1 from BS fair
            if max_buy > 0 and fair > 0.5:
                orders.append(Order(vev, math.floor(fair - 1), max_buy))
            if max_sell > 0 and fair > 0.5:
                orders.append(Order(vev, math.ceil(fair + 1), -max_sell))

            if orders:
                result[vev] = orders

        # ── Save state ─────────────────────────────────────────────────────────
        new_td = {
            "hp_ema":  hp_ema,
            "vf_ema":  vf_ema,
            "day":     day,
            "prev_ts": prev_ts,
        }

        return result, 0, jsonpickle.encode(new_td)