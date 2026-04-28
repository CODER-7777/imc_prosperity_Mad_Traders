# Mad_Traders - IMC Prosperity 4 - Round 3 "Gloves Off" - V3 KILLER
# ==================================================================
# FIXES IN V3:
#   1. OrderManager: Mathematically prevents exchange rejection due to limits.
#   2. Theta Exit Strategy: Close profitable "snipe" inventory at fair value.
#   3. Correct VE order sequencing: Delta hedge first, MM with remaining capacity.
#   4. Fallback Sigma: 0.16 (calibrated from historical data).
# ==================================================================

from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List, Dict, Tuple
import math
import json


class OrderManager:
    """Safely accumulates orders without ever exceeding position limits."""
    def __init__(self, product: str, current_pos: int, limit: int):
        self.product = product
        self.pos = current_pos
        self.limit = limit
        self.orders: List[Order] = []
        self.buy_vol = 0
        self.sell_vol = 0

    def add_buy(self, price: int, qty: int) -> int:
        if qty <= 0:
            return 0
        max_buy = self.limit - (self.pos + self.buy_vol)
        actual_buy = min(qty, max_buy)
        if actual_buy > 0:
            self.orders.append(Order(self.product, price, actual_buy))
            self.buy_vol += actual_buy
            return actual_buy
        return 0

    def add_sell(self, price: int, qty: int) -> int:
        if qty >= 0:
            return 0
        # We can sell until position reaches -limit.
        # current absolute minimum is -limit.
        # available sell room is (-limit) - (current_pos + sell_vol)
        max_sell = -self.limit - (self.pos + self.sell_vol)
        actual_sell = max(qty, max_sell) # max because quantities are negative
        if actual_sell < 0:
            self.orders.append(Order(self.product, price, actual_sell))
            self.sell_vol += actual_sell
            return actual_sell
        return 0


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

    # Strategy categorizations
    DEEP_ITM = {"VEV_4000", "VEV_4500"}
    MOD_ITM = {"VEV_5000"}
    NEAR_ATM = {"VEV_5100", "VEV_5200", "VEV_5300"}
    SKIP_OTM = {"VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"}

    TICKS_PER_DAY = 1_000_000
    TTE_START_DAYS = 5.0
    FALLBACK_SIGMA = 0.16

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

    # ===== IMPLIED VOL EXTRACTION =====
    @staticmethod
    def implied_vol(S: float, K: float, T: float, market_price: float) -> float:
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
    def trade_delta1(self, om: OrderManager, od: OrderDepth, fv: float,
                     spread: int = 2, skew_k: float = 4.0):
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return

        # TAKE mispriced
        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - 0.5:
                om.add_buy(ask_p, -od.sell_orders[ask_p])

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + 0.5:
                om.add_sell(bid_p, -od.buy_orders[bid_p])

        # MAKE with inventory skew
        # Calculate skew based on theoretical position after takes
        virtual_pos = om.pos + om.buy_vol + om.sell_vol
        inv_ratio = virtual_pos / om.limit if om.limit > 0 else 0
        skew = -int(inv_ratio * skew_k)
        fv_r = int(round(fv))

        my_bid = min(fv_r - spread + skew, bb + 1)
        my_ask = max(fv_r + spread + skew, ba - 1)

        om.add_buy(my_bid, om.limit * 2) # It will clamp to available room
        om.add_sell(my_ask, -om.limit * 2)

    # ===== STRATEGY: Deep ITM option MM =====
    def trade_deep_itm(self, om: OrderManager, od: OrderDepth, strike: int,
                       ve_price: float, T_years: float, sigma: float):
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return

        fv = self.bs_call(ve_price, float(strike), T_years, sigma)
        fv = max(fv, max(0.0, ve_price - strike))
        edge = max(2.0, fv * 0.005)

        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - edge:
                om.add_buy(ask_p, -od.sell_orders[ask_p])

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + edge:
                om.add_sell(bid_p, -od.buy_orders[bid_p])

        # Make liquidity (20 lots max)
        virtual_pos = om.pos + om.buy_vol + om.sell_vol
        inv_ratio = virtual_pos / om.limit if om.limit > 0 else 0
        skew = -int(inv_ratio * 3)
        fv_int = int(round(fv))

        my_bid = max(0, min(fv_int - 2 + skew, bb + 1))
        my_ask = max(1, max(fv_int + 2 + skew, ba - 1))

        om.add_buy(my_bid, 20)
        om.add_sell(my_ask, -20)

    # ===== STRATEGY: Near-ATM Sniping + THETA EXIT =====
    def trade_atm_snipe(self, om: OrderManager, od: OrderDepth, strike: int,
                        ve_price: float, T_years: float, sigma: float):
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return

        fv = self.bs_call(ve_price, float(strike), T_years, sigma)
        fv = max(fv, max(0.0, ve_price - strike))
        edge = max(3.0, fv * 0.05)

        # 1. Close inventory (THETA EXIT STRATEGY)
        # If we are long, post sell orders at fair value to exit.
        # If we are short, post buy orders at fair value to exit.
        if om.pos > 0:
            exit_price = max(int(round(fv)) + 1, ba - 1 if ba else 0)
            if exit_price > 0:
                om.add_sell(exit_price, -om.pos) # Try to close entire position
        elif om.pos < 0:
            exit_price = min(int(round(fv)) - 1, bb + 1 if bb else 999999)
            if exit_price > 0:
                om.add_buy(exit_price, -om.pos)

        # 2. Snipe massive mispricings (soft limit to ±100 to reduce gamma risk)
        # We manually check if virtual_pos < 100 before taking.
        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - edge:
                virtual_pos = om.pos + om.buy_vol + om.sell_vol
                room = max(0, 100 - virtual_pos)
                take_qty = min(-od.sell_orders[ask_p], room)
                if take_qty > 0:
                    om.add_buy(ask_p, take_qty)

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + edge:
                virtual_pos = om.pos + om.buy_vol + om.sell_vol
                room = max(0, virtual_pos + 100) # Since pos is negative, this is 100 - abs(pos)
                take_qty = min(od.buy_orders[bid_p], room)
                if take_qty > 0:
                    om.add_sell(bid_p, -take_qty)

    # ===== STRATEGY: Moderate ITM =====
    def trade_mod_itm(self, om: OrderManager, od: OrderDepth, strike: int,
                      ve_price: float, T_years: float, sigma: float):
        bb, ba = self.get_best(od)
        if bb is None or ba is None:
            return

        fv = self.bs_call(ve_price, float(strike), T_years, sigma)
        fv = max(fv, max(0.0, ve_price - strike))
        edge = max(2.0, fv * 0.02)

        for ask_p in sorted(od.sell_orders.keys()):
            if ask_p < fv - edge:
                om.add_buy(ask_p, -od.sell_orders[ask_p])

        for bid_p in sorted(od.buy_orders.keys(), reverse=True):
            if bid_p > fv + edge:
                om.add_sell(bid_p, -od.buy_orders[bid_p])

        virtual_pos = om.pos + om.buy_vol + om.sell_vol
        inv_ratio = virtual_pos / om.limit if om.limit > 0 else 0
        skew = -int(inv_ratio * 3)
        fv_int = int(round(fv))

        my_bid = max(0, min(fv_int - 3 + skew, bb + 1))
        my_ask = max(1, max(fv_int + 3 + skew, ba - 1))

        om.add_buy(my_bid, 10)
        om.add_sell(my_ask, -10)

    # ===== DELTA HEDGING =====
    def calc_portfolio_delta(self, state: TradingState, ve_price: float,
                             T_years: float, sigma: float) -> float:
        total_delta = 0.0
        for product, strike in self.VEV_STRIKES.items():
            pos = state.position.get(product, 0)
            if pos != 0:
                d = self.bs_delta(ve_price, float(strike), T_years, sigma)
                total_delta += pos * d
        total_delta += state.position.get("VELVETFRUIT_EXTRACT", 0)
        return total_delta

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

        if 0 < last_ts and state.timestamp < last_ts:
            day += 1

        # ---- VE MID PRICE ----
        ve_mid = 5270.0
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            m = self.get_mid(state.order_depths["VELVETFRUIT_EXTRACT"])
            if m > 0:
                ve_mid = m

        # ---- UPDATE EMAs ----
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

        # ---- EXTRACT IMPLIED VOL ----
        sigma = prev_sigma
        for calib_prod in ["VEV_5300", "VEV_5200"]:
            if calib_prod in state.order_depths:
                od_c = state.order_depths[calib_prod]
                mid_c = self.get_mid(od_c)
                if mid_c > 1.0:
                    K = float(self.VEV_STRIKES[calib_prod])
                    iv = self.implied_vol(ve_mid, K, T_years, mid_c)
                    if 0.05 < iv < 2.0:
                        sigma = 0.3 * iv + 0.7 * prev_sigma
                        break

        # ---- TRADE HYDROGEL ----
        if "HYDROGEL_PACK" in state.order_depths:
            od = state.order_depths["HYDROGEL_PACK"]
            pos = state.position.get("HYDROGEL_PACK", 0)
            fv = ema.get("HYDROGEL_PACK", self.get_mid(od))
            om = OrderManager("HYDROGEL_PACK", pos, self.LIMITS["HYDROGEL_PACK"])
            self.trade_delta1(om, od, fv, spread=3, skew_k=5.0)
            result["HYDROGEL_PACK"] = om.orders

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
            om = OrderManager(product, pos, limit)

            if not od.buy_orders or not od.sell_orders:
                result[product] = []
                continue

            if product in self.SKIP_OTM:
                pass
            elif product in self.DEEP_ITM:
                self.trade_deep_itm(om, od, strike, ve_mid, T_years, sigma)
            elif product in self.MOD_ITM:
                self.trade_mod_itm(om, od, strike, ve_mid, T_years, sigma)
            elif product in self.NEAR_ATM:
                self.trade_atm_snipe(om, od, strike, ve_mid, T_years, sigma)

            result[product] = om.orders

        # ---- TRADE VE & DELTA HEDGE ----
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            od = state.order_depths["VELVETFRUIT_EXTRACT"]
            pos = state.position.get("VELVETFRUIT_EXTRACT", 0)
            fv = ema.get("VELVETFRUIT_EXTRACT", ve_mid)
            om = OrderManager("VELVETFRUIT_EXTRACT", pos, self.LIMITS["VELVETFRUIT_EXTRACT"])

            # 1. Delta hedge first (uses up position limit aggressively if needed)
            net_delta = self.calc_portfolio_delta(state, ve_mid, T_years, sigma)
            if abs(net_delta) > 20:
                hedge_qty = -int(round(net_delta * 0.5))
                bb, ba = self.get_best(od)
                if bb is not None and ba is not None:
                    if hedge_qty > 0:
                        om.add_buy(ba, hedge_qty)
                    elif hedge_qty < 0:
                        om.add_sell(bb, hedge_qty)

            # 2. Market make with whatever position limit is left!
            self.trade_delta1(om, od, fv, spread=2, skew_k=3.0)
            result["VELVETFRUIT_EXTRACT"] = om.orders

        # ---- SAVE STATE ----
        conversions = 0
        trader_data = json.dumps({
            "ema": ema,
            "day": day,
            "last_ts": state.timestamp,
            "sigma": sigma,
        })

        return result, conversions, trader_data