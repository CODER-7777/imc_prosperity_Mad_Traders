# Mad_Traders - IMC Prosperity 4 - Round 3 "Gloves Off" - V2 KILLER
# ==================================================================
# FIXES FROM LOG ANALYSIS (submission 384630 → only +377):
#   1. IMPLIED VOL from market (not hardcoded σ=0.22)
#   2. DELTA HEDGING via VE (was missing entirely)
#   3. TAKE-ONLY on risky near-ATM options (no MM on VEV_5100-5500)
#   4. AGGRESSIVE MM only on HYDROGEL + deep ITM options
#   5. SKIP worthless OTM (VEV_5400+)
#   6. FASTER EMA (α=0.05 not 0.005)
# ==================================================================

from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict, Tuple
import math
import json


class Trader:

    LIMITS = {
        "HYDROGEL_PACK": 200,
        "VELVETFRUIT_EXTRACT": 200,
        "VEV_4000": 300, "VEV_4500": 300, "VEV_5000": 300,
        "VEV_5100": 300, "VEV_5200": 300, "VEV_5300": 300,
        "VEV_5400": 300, "VEV_5500": 300, "VEV_6000": 300,
        "VEV_6500": 300,
    }

    VEV_STRIKES = {
        "VEV_4000": 4000, "VEV_4500": 4500, "VEV_5000": 5000,
        "VEV_5100": 5100, "VEV_5200": 5200, "VEV_5300": 5300,
        "VEV_5400": 5400, "VEV_5500": 5500, "VEV_6000": 6000,
        "VEV_6500": 6500,
    }

    # Deep ITM = safe to market-make (behave like underlying)
    DEEP_ITM = {"VEV_4000", "VEV_4500"}
    # Moderate ITM = market-make with caution
    MOD_ITM = {"VEV_5000"}
    # Near ATM = TAKE ONLY, never provide liquidity
    NEAR_ATM = {"VEV_5100", "VEV_5200", "VEV_5300"}
    # OTM = SKIP entirely (worthless, pure gamma risk)
    SKIP_OTM = {"VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"}

    TICKS_PER_DAY = 1_000_000
    TTE_START_DAYS = 5.0
    FALLBACK_SIGMA = 0.18

    # ===== BLACK-SCHOLES =====
    @staticmethod
    def norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / 1.4142135623730951))

    @staticmethod
    def bs_call(S: float, K: float, T: float, sigma: float) -> float:
        if T <= 1e-7:
            return max(0.0, S - K)
        if S <= 0 or K <= 0 or sigma <= 0:
            return max(0.0, S - K)
        try:
            sqrt_T = math.sqrt(T)
            d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrt_T)
            d2 = d1 - sigma * sqrt_T
            return S * Trader.norm_cdf(d1) - K * Trader.norm_cdf(d2)
        except (ValueError, ZeroDivisionError):
            return max(0.0, S - K)

    @staticmethod
    def bs_delta(S: float, K: float, T: float, sigma: float) -> float:
        if T <= 1e-7:
            return 1.0 if S > K else 0.0
        if S <= 0 or K <= 0 or sigma <= 0:
            return 1.0 if S > K else 0.0
        try:
            sqrt_T = math.sqrt(T)
            d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * sqrt_T)
            return Trader.norm_cdf(d1)
        except (ValueError, ZeroDivisionError):
            return 1.0 if S > K else 0.0

    # ===== IMPLIED VOL EXTRACTION (bisection) =====
    @staticmethod
    def implied_vol(S: float, K: float, T: float, market_price: float) -> float:
        """Extract implied vol from market option price using bisection."""
        if T <= 1e-7 or market_price <= 0 or S <= 0 or K <= 0:
            return Trader.FALLBACK_SIGMA
        intrinsic = max(0.0, S - K)
        if market_price <= intrinsic + 0.01:
            return 0.01
        lo, hi = 0.01, 3.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            price = Trader.bs_call(S, K, T, mid)
            if price < market_price:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    # ===== HELPERS =====
    @staticmethod
    def get_mid(od: OrderDepth) -> float:
        if od.buy_orders and od.sell_orders:
            return (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
        return 0.0

    @staticmethod
    def get_best(od: OrderDepth) -> Tuple:
        bb = max(od.buy_orders.keys()) if od.buy_orders else None
        ba = min(od.sell_orders.keys()) if od.sell_orders else None
        return bb, ba

    # ===== STRATEGY: Aggressive MM for delta-1 products =====
    def trade_delta1(self, product: str, od: OrderDepth, pos: int,
                     limit: int, fv: float, spread: int = 2,
                     skew_k: float = 4.0) -> List[Order]:
        orders: List[Order] = []
        cur_pos = pos
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return orders

        # TAKE mispriced
        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - 0.5 and cur_pos < limit:
                vol = min(-od.sell_orders[ask_p], limit - cur_pos)
                if vol > 0:
                    orders.append(Order(product, ask_p, vol))
                    cur_pos += vol

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + 0.5 and cur_pos > -limit:
                vol = min(od.buy_orders[bid_p], cur_pos + limit)
                if vol > 0:
                    orders.append(Order(product, bid_p, -vol))
                    cur_pos -= vol

        # MAKE with inventory skew
        inv_ratio = cur_pos / limit if limit > 0 else 0
        skew = -int(inv_ratio * skew_k)
        fv_r = int(round(fv))

        my_bid = min(fv_r - spread + skew, bb + 1)
        my_ask = max(fv_r + spread + skew, ba - 1)

        buy_room = limit - cur_pos
        sell_room = limit + cur_pos
        if buy_room > 0:
            orders.append(Order(product, my_bid, buy_room))
        if sell_room > 0:
            orders.append(Order(product, my_ask, -sell_room))

        return orders

    # ===== STRATEGY: Deep ITM option MM (synthetic underlying) =====
    def trade_deep_itm(self, product: str, od: OrderDepth, pos: int,
                       limit: int, strike: int, ve_price: float,
                       T_years: float, sigma: float) -> List[Order]:
        orders: List[Order] = []
        cur_pos = pos
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return orders

        fv = self.bs_call(ve_price, float(strike), T_years, sigma)
        fv = max(fv, max(0.0, ve_price - strike))

        # TAKE mispriced (tight edge for deep ITM)
        edge = max(2.0, fv * 0.005)
        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - edge and cur_pos < limit:
                vol = min(-od.sell_orders[ask_p], limit - cur_pos)
                if vol > 0:
                    orders.append(Order(product, ask_p, vol))
                    cur_pos += vol

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + edge and cur_pos > -limit:
                vol = min(od.buy_orders[bid_p], cur_pos + limit)
                if vol > 0:
                    orders.append(Order(product, bid_p, -vol))
                    cur_pos -= vol

        # MAKE with conservative size (20 lots, not 40)
        inv_ratio = cur_pos / limit if limit > 0 else 0
        skew = -int(inv_ratio * 3)
        fv_int = int(round(fv))

        my_bid = max(0, min(fv_int - 2 + skew, bb + 1))
        my_ask = max(1, max(fv_int + 2 + skew, ba - 1))

        mm_size = 20
        buy_room = min(mm_size, limit - cur_pos)
        sell_room = min(mm_size, cur_pos + limit)

        if my_bid > 0 and buy_room > 0:
            orders.append(Order(product, my_bid, buy_room))
        if my_ask > 0 and sell_room > 0:
            orders.append(Order(product, my_ask, -sell_room))

        return orders

    # ===== STRATEGY: Near-ATM TAKE-ONLY (no market-making!) =====
    def trade_atm_snipe(self, product: str, od: OrderDepth, pos: int,
                        limit: int, strike: int, ve_price: float,
                        T_years: float, sigma: float) -> List[Order]:
        """Only take clearly mispriced options. NO market-making."""
        orders: List[Order] = []
        cur_pos = pos
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return orders

        fv = self.bs_call(ve_price, float(strike), T_years, sigma)
        fv = max(fv, max(0.0, ve_price - strike))

        # WIDE edge requirement (5% or 3 ticks minimum)
        edge = max(3.0, fv * 0.05)

        # Cap position to ±100 (not full 300) to limit gamma exposure
        soft_limit = min(100, limit)

        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - edge and cur_pos < soft_limit:
                vol = min(-od.sell_orders[ask_p], soft_limit - cur_pos)
                if vol > 0:
                    orders.append(Order(product, ask_p, vol))
                    cur_pos += vol

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + edge and cur_pos > -soft_limit:
                vol = min(od.buy_orders[bid_p], cur_pos + soft_limit)
                if vol > 0:
                    orders.append(Order(product, bid_p, -vol))
                    cur_pos -= vol

        return orders

    # ===== STRATEGY: Moderate ITM option trading =====
    def trade_mod_itm(self, product: str, od: OrderDepth, pos: int,
                      limit: int, strike: int, ve_price: float,
                      T_years: float, sigma: float) -> List[Order]:
        orders: List[Order] = []
        cur_pos = pos
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return orders

        fv = self.bs_call(ve_price, float(strike), T_years, sigma)
        fv = max(fv, max(0.0, ve_price - strike))

        edge = max(2.0, fv * 0.02)

        # Take mispriced
        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - edge and cur_pos < limit:
                vol = min(-od.sell_orders[ask_p], limit - cur_pos)
                if vol > 0:
                    orders.append(Order(product, ask_p, vol))
                    cur_pos += vol

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + edge and cur_pos > -limit:
                vol = min(od.buy_orders[bid_p], cur_pos + limit)
                if vol > 0:
                    orders.append(Order(product, bid_p, -vol))
                    cur_pos -= vol

        # Small MM (10 lots only)
        inv_ratio = cur_pos / limit if limit > 0 else 0
        skew = -int(inv_ratio * 3)
        fv_int = int(round(fv))

        my_bid = max(0, min(fv_int - 3 + skew, bb + 1))
        my_ask = max(1, max(fv_int + 3 + skew, ba - 1))

        mm_size = 10
        buy_room = min(mm_size, limit - cur_pos)
        sell_room = min(mm_size, cur_pos + limit)

        if my_bid > 0 and buy_room > 0:
            orders.append(Order(product, my_bid, buy_room))
        if my_ask > 0 and sell_room > 0:
            orders.append(Order(product, my_ask, -sell_room))

        return orders

    # ===== DELTA HEDGING =====
    def calc_portfolio_delta(self, state: TradingState, ve_price: float,
                             T_years: float, sigma: float) -> float:
        """Calculate total portfolio delta from all option positions."""
        total_delta = 0.0
        for product, strike in self.VEV_STRIKES.items():
            pos = state.position.get(product, 0)
            if pos != 0:
                d = self.bs_delta(ve_price, float(strike), T_years, sigma)
                total_delta += pos * d
        # Add VE position directly (delta = 1)
        total_delta += state.position.get("VELVETFRUIT_EXTRACT", 0)
        return total_delta

    def delta_hedge_orders(self, od: OrderDepth, ve_pos: int,
                           target_ve_trade: int, limit: int) -> List[Order]:
        """Generate VE orders to hedge portfolio delta."""
        orders: List[Order] = []
        if target_ve_trade == 0:
            return orders

        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return orders

        if target_ve_trade > 0:
            # Need to BUY VE
            buy_room = limit - ve_pos
            qty = min(target_ve_trade, buy_room)
            if qty > 0:
                orders.append(Order("VELVETFRUIT_EXTRACT", ba, qty))
        elif target_ve_trade < 0:
            # Need to SELL VE
            sell_room = ve_pos + limit
            qty = min(-target_ve_trade, sell_room)
            if qty > 0:
                orders.append(Order("VELVETFRUIT_EXTRACT", bb, -qty))

        return orders

    # ===== MAIN RUN =====
    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        # ---- RESTORE STATE ----
        ema = {}
        day = 0
        last_ts = -1
        prev_sigma = self.FALLBACK_SIGMA

        if state.traderData and state.traderData != "":
            try:
                saved = json.loads(state.traderData)
                ema = saved.get("ema", {})
                day = saved.get("day", 0)
                last_ts = saved.get("last_ts", -1)
                prev_sigma = saved.get("sigma", self.FALLBACK_SIGMA)
            except Exception:
                pass

        # ---- DAY TRANSITION ----
        if 0 < last_ts and state.timestamp < last_ts:
            day += 1

        # ---- VE MID PRICE ----
        ve_mid = 5270.0  # sensible default
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            m = self.get_mid(state.order_depths["VELVETFRUIT_EXTRACT"])
            if m > 0:
                ve_mid = m

        # ---- UPDATE EMAs (fast α=0.05) ----
        alpha = 0.05
        for prod in ["VELVETFRUIT_EXTRACT", "HYDROGEL_PACK"]:
            if prod in state.order_depths:
                mid = self.get_mid(state.order_depths[prod])
                if mid > 0:
                    if prod in ema:
                        ema[prod] = alpha * mid + (1.0 - alpha) * ema[prod]
                    else:
                        ema[prod] = mid

        # ---- TTE ----
        intraday_frac = state.timestamp / self.TICKS_PER_DAY
        tte_days = max(0.01, self.TTE_START_DAYS - day - intraday_frac)
        T_years = tte_days / 365.0

        # ---- EXTRACT IMPLIED VOL from nearest ATM option ----
        sigma = prev_sigma
        # Use VEV_5200 or VEV_5300 (near ATM for VE ~5270)
        for calib_prod in ["VEV_5300", "VEV_5200"]:
            if calib_prod in state.order_depths:
                od_c = state.order_depths[calib_prod]
                mid_c = self.get_mid(od_c)
                if mid_c > 1.0:
                    K = float(self.VEV_STRIKES[calib_prod])
                    iv = self.implied_vol(ve_mid, K, T_years, mid_c)
                    if 0.05 < iv < 2.0:
                        # Smooth with previous to avoid jumps
                        sigma = 0.3 * iv + 0.7 * prev_sigma
                        break

        # ---- TRADE HYDROGEL (pure MM, always profitable) ----
        if "HYDROGEL_PACK" in state.order_depths:
            od = state.order_depths["HYDROGEL_PACK"]
            pos = state.position.get("HYDROGEL_PACK", 0)
            fv = ema.get("HYDROGEL_PACK", self.get_mid(od))
            result["HYDROGEL_PACK"] = self.trade_delta1(
                "HYDROGEL_PACK", od, pos, 200, fv, spread=3, skew_k=5.0)

        # ---- TRADE VE (MM + delta hedge component) ----
        ve_mm_orders: List[Order] = []
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            od = state.order_depths["VELVETFRUIT_EXTRACT"]
            pos = state.position.get("VELVETFRUIT_EXTRACT", 0)
            fv = ema.get("VELVETFRUIT_EXTRACT", ve_mid)
            ve_mm_orders = self.trade_delta1(
                "VELVETFRUIT_EXTRACT", od, pos, 200, fv, spread=2, skew_k=3.0)

        # ---- TRADE OPTIONS BY CATEGORY ----
        for product in state.order_depths:
            if product in ("HYDROGEL_PACK", "VELVETFRUIT_EXTRACT"):
                continue
            if product not in self.VEV_STRIKES:
                result[product] = []
                continue

            od = state.order_depths[product]
            pos = state.position.get(product, 0)
            limit = self.LIMITS.get(product, 300)
            strike = self.VEV_STRIKES[product]

            if not od.buy_orders or not od.sell_orders:
                result[product] = []
                continue

            if product in self.SKIP_OTM:
                # Don't touch OTM options at all
                result[product] = []
            elif product in self.DEEP_ITM:
                result[product] = self.trade_deep_itm(
                    product, od, pos, limit, strike, ve_mid, T_years, sigma)
            elif product in self.MOD_ITM:
                result[product] = self.trade_mod_itm(
                    product, od, pos, limit, strike, ve_mid, T_years, sigma)
            elif product in self.NEAR_ATM:
                result[product] = self.trade_atm_snipe(
                    product, od, pos, limit, strike, ve_mid, T_years, sigma)
            else:
                result[product] = []

        # ---- DELTA HEDGING ----
        # Calculate net portfolio delta AFTER option orders
        net_delta = self.calc_portfolio_delta(state, ve_mid, T_years, sigma)

        # We want net delta ≈ 0. If |delta| > 20, hedge aggressively
        ve_pos = state.position.get("VELVETFRUIT_EXTRACT", 0)
        ve_limit = self.LIMITS["VELVETFRUIT_EXTRACT"]

        hedge_qty = 0
        if abs(net_delta) > 20:
            # Hedge to bring delta toward 0
            hedge_qty = -int(round(net_delta * 0.5))  # partial hedge (50%)
            # Clamp to position limits
            if hedge_qty > 0:
                hedge_qty = min(hedge_qty, ve_limit - ve_pos)
            elif hedge_qty < 0:
                hedge_qty = max(hedge_qty, -(ve_pos + ve_limit))

        # Merge hedge orders with VE MM orders
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            od_ve = state.order_depths["VELVETFRUIT_EXTRACT"]
            if hedge_qty != 0:
                hedge_orders = self.delta_hedge_orders(
                    od_ve, ve_pos, hedge_qty, ve_limit)
                # Combine: hedge orders go first (priority), then MM
                result["VELVETFRUIT_EXTRACT"] = hedge_orders + ve_mm_orders
            else:
                result["VELVETFRUIT_EXTRACT"] = ve_mm_orders

        # ---- SAVE STATE ----
        conversions = 0
        trader_data = json.dumps({
            "ema": ema,
            "day": day,
            "last_ts": state.timestamp,
            "sigma": sigma,
        })

        return result, conversions, trader_data