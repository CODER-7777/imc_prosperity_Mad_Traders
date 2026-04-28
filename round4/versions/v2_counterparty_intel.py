"""
IMC Prosperity 4 - Round 4 Strategy
Team: Mad_Traders

Products:
  - HYDROGEL_PACK (delta-1, FV ~10000, mean-reverting)
  - VELVETFRUIT_EXTRACT (delta-1, FV ~5245, noisy trending)
  - VEV_4000..VEV_6500 (10 call options on VELVETFRUIT_EXTRACT)

Strategy:
  1. HP: Market-making around FV=10000 with inventory skew
  2. VE: EMA-based market-making with trend bias
  3. VEV deep ITM (4000, 4500): Track intrinsic value = VE - strike
  4. VEV near ATM (5000-5400): Black-Scholes fair value market-making
  5. VEV far OTM (5500, 6000, 6500): Sell aggressively (near-worthless)
"""
from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import math
import json


def norm_cdf(x: float) -> float:
    """Approximation of the standard normal CDF (Abramowitz & Stegun)."""
    if x < -10:
        return 0.0
    if x > 10:
        return 1.0
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911
    sign = 1.0
    if x < 0:
        sign = -1.0
        x = -x
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x / 2.0)
    return 0.5 * (1.0 + sign * y)


def bs_call_price(S: float, K: float, T: float, sigma: float) -> float:
    """Black-Scholes call option price. S=underlying, K=strike, T=time in years, sigma=annual vol."""
    if T <= 0:
        return max(0.0, S - K)
    if sigma <= 0:
        return max(0.0, S - K)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * norm_cdf(d1) - K * norm_cdf(d2)


class Trader:
    def bid(self):
        return 15

    def __init__(self):
        self.limits = {
            "HYDROGEL_PACK": 200,
            "VELVETFRUIT_EXTRACT": 200,
            "VEV_4000": 300,
            "VEV_4500": 300,
            "VEV_5000": 300,
            "VEV_5100": 300,
            "VEV_5200": 300,
            "VEV_5300": 300,
            "VEV_5400": 300,
            "VEV_5500": 300,
            "VEV_6000": 300,
            "VEV_6500": 300,
        }
        self.strikes = {
            "VEV_4000": 4000, "VEV_4500": 4500,
            "VEV_5000": 5000, "VEV_5100": 5100,
            "VEV_5200": 5200, "VEV_5300": 5300,
            "VEV_5400": 5400, "VEV_5500": 5500,
            "VEV_6000": 6000, "VEV_6500": 6500,
        }
        # Implied vol calibrated from historical data (time values on VEV_5200)
        # VE ~5250, VEV_5200 time value ~35-50 with TTE 5-7 days
        # This corresponds to ~0.16 annualized vol (using 252 trading days)
        self.sigma = 0.18
        self.trading_days_per_year = 252

    def run(self, state: TradingState):
        result = {}
        conversions = 0

        # ===== RESTORE STATE =====
        ve_ema = 5245.0  # default
        tick_count = 0
        if state.traderData:
            try:
                saved = json.loads(state.traderData)
                ve_ema = saved.get("ve_ema", 5245.0)
                tick_count = saved.get("tick_count", 0)
            except:
                pass
        tick_count += 1

        # ===== GET CURRENT MID PRICES =====
        def get_mid(od: OrderDepth):
            if od.buy_orders and od.sell_orders:
                return (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
            elif od.buy_orders:
                return max(od.buy_orders.keys())
            elif od.sell_orders:
                return min(od.sell_orders.keys())
            return None

        ve_mid = None
        if "VELVETFRUIT_EXTRACT" in state.order_depths:
            ve_mid = get_mid(state.order_depths["VELVETFRUIT_EXTRACT"])
        if ve_mid is not None:
            alpha = 0.15
            ve_ema = alpha * ve_mid + (1 - alpha) * ve_ema

        # Time to expiry for Round 4: TTE = 4 days (7 - 4 + 1 = 4 at start, decreasing within day)
        # Within a day, timestamp goes from 0 to 999900 (100-tick intervals, 10000 ticks)
        # So TTE in years = (4 - timestamp/1000000) / trading_days_per_year
        ts = state.timestamp
        day_fraction = ts / 1000000.0  # 0.0 to ~1.0
        tte_days = max(4.0 - day_fraction, 0.01)
        tte_years = tte_days / self.trading_days_per_year

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            position = state.position.get(product, 0)
            limit = self.limits.get(product, 200)

            best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
            best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None

            if best_bid is None and best_ask is None:
                result[product] = orders
                continue

            mid = get_mid(order_depth)

            # ==========================================
            # HYDROGEL_PACK - Mean-revert around 10000
            # ==========================================
            if product == "HYDROGEL_PACK":
                fv = 10000
                # Aggressive taking
                if best_ask is not None:
                    for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                        if ask < fv - 1 and position < limit:
                            buy_vol = min(limit - position, -ask_vol)
                            if buy_vol > 0:
                                orders.append(Order(product, ask, buy_vol))
                                position += buy_vol

                if best_bid is not None:
                    for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                        if bid > fv + 1 and position > -limit:
                            sell_vol = max(-limit - position, -bid_vol)
                            if sell_vol < 0:
                                orders.append(Order(product, bid, sell_vol))
                                position += sell_vol

                # Passive market-making with inventory skew
                skew = -int((position / limit) * 4)
                my_bid = fv - 3 + skew
                my_ask = fv + 3 + skew

                if best_bid is not None:
                    my_bid = min(my_bid, best_bid + 1)
                if best_ask is not None:
                    my_ask = max(my_ask, best_ask - 1)

                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -(limit + position)))

            # ==========================================
            # VELVETFRUIT_EXTRACT - EMA-based MM
            # ==========================================
            elif product == "VELVETFRUIT_EXTRACT":
                fv = int(round(ve_ema))

                # Aggressive taking
                if best_ask is not None:
                    for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                        if ask < fv - 1 and position < limit:
                            buy_vol = min(limit - position, -ask_vol)
                            if buy_vol > 0:
                                orders.append(Order(product, ask, buy_vol))
                                position += buy_vol

                if best_bid is not None:
                    for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                        if bid > fv + 1 and position > -limit:
                            sell_vol = max(-limit - position, -bid_vol)
                            if sell_vol < 0:
                                orders.append(Order(product, bid, sell_vol))
                                position += sell_vol

                # Passive making
                skew = -int((position / limit) * 3)
                my_bid = fv - 2 + skew
                my_ask = fv + 2 + skew

                if best_bid is not None:
                    my_bid = min(my_bid, best_bid + 1)
                if best_ask is not None:
                    my_ask = max(my_ask, best_ask - 1)

                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -(limit + position)))

            # ==========================================
            # VEV OPTIONS
            # ==========================================
            elif product in self.strikes and ve_mid is not None:
                strike = self.strikes[product]

                # Compute BS fair value
                bs_fv = bs_call_price(ve_mid, strike, tte_years, self.sigma)
                intrinsic = max(0.0, ve_mid - strike)

                # For deep ITM options (4000, 4500), fair value ≈ intrinsic
                # For near ATM (5000-5300), use BS
                # For far OTM (5400+), BS gives small values, sell aggressively

                if strike <= 4500:
                    # Deep ITM: track intrinsic closely
                    fv = max(intrinsic, bs_fv)
                    fv_int = int(round(fv))
                    spread = 3

                    # Take mispriced orders
                    if best_ask is not None:
                        for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                            if ask < fv_int - 1 and position < limit:
                                buy_vol = min(limit - position, -ask_vol)
                                if buy_vol > 0:
                                    orders.append(Order(product, ask, buy_vol))
                                    position += buy_vol

                    if best_bid is not None:
                        for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                            if bid > fv_int + 1 and position > -limit:
                                sell_vol = max(-limit - position, -bid_vol)
                                if sell_vol < 0:
                                    orders.append(Order(product, bid, sell_vol))
                                    position += sell_vol

                    # Market-make around FV
                    skew = -int((position / limit) * 2)
                    my_bid = fv_int - spread + skew
                    my_ask = fv_int + spread + skew

                    if best_bid is not None:
                        my_bid = min(my_bid, best_bid + 1)
                    if best_ask is not None:
                        my_ask = max(my_ask, best_ask - 1)

                    if my_bid > 0 and position < limit:
                        orders.append(Order(product, my_bid, limit - position))
                    if my_ask > 0 and position > -limit:
                        orders.append(Order(product, my_ask, -(limit + position)))

                elif strike <= 5300:
                    # Near ATM: Use BS fair value, wider spread
                    fv_int = int(round(bs_fv))
                    if fv_int < 1:
                        fv_int = 1
                    spread = max(2, int(round(bs_fv * 0.04)))  # 4% spread

                    # Take mispriced orders
                    if best_ask is not None:
                        for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                            if ask < fv_int - spread and position < limit:
                                buy_vol = min(limit - position, -ask_vol)
                                if buy_vol > 0:
                                    orders.append(Order(product, ask, buy_vol))
                                    position += buy_vol

                    if best_bid is not None:
                        for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                            if bid > fv_int + spread and position > -limit:
                                sell_vol = max(-limit - position, -bid_vol)
                                if sell_vol < 0:
                                    orders.append(Order(product, bid, sell_vol))
                                    position += sell_vol

                    # Market-make
                    skew = -int((position / limit) * 2)
                    my_bid = fv_int - spread + skew
                    my_ask = fv_int + spread + skew

                    if best_bid is not None:
                        my_bid = min(my_bid, best_bid + 1)
                    if best_ask is not None:
                        my_ask = max(my_ask, best_ask - 1)

                    if my_bid > 0 and position < limit:
                        orders.append(Order(product, my_bid, limit - position))
                    if my_ask > 0 and position > -limit:
                        orders.append(Order(product, my_ask, -(limit + position)))

                else:
                    # Far OTM (5400, 5500, 6000, 6500): Sell aggressively
                    fv_int = max(1, int(round(bs_fv)))

                    # Buy cheap if available
                    if best_ask is not None:
                        for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                            if ask < max(1, fv_int - 2) and position < limit:
                                buy_vol = min(limit - position, -ask_vol)
                                if buy_vol > 0:
                                    orders.append(Order(product, ask, buy_vol))
                                    position += buy_vol

                    # Sell at any positive bid
                    if best_bid is not None:
                        for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                            if bid >= max(1, fv_int) and position > -limit:
                                sell_vol = max(-limit - position, -bid_vol)
                                if sell_vol < 0:
                                    orders.append(Order(product, bid, sell_vol))
                                    position += sell_vol

                    # Post aggressive asks
                    my_ask = max(1, fv_int + 1)
                    if best_ask is not None:
                        my_ask = max(my_ask, best_ask - 1)
                    if position > -limit:
                        orders.append(Order(product, my_ask, -(limit + position)))

                    # Post small bid for cheap buys
                    my_bid = max(1, fv_int - 2)
                    if best_bid is not None:
                        my_bid = min(my_bid, best_bid + 1)
                    if my_bid > 0 and position < limit:
                        qty = min(50, limit - position)
                        if qty > 0:
                            orders.append(Order(product, my_bid, qty))

            result[product] = orders

        # ===== SAVE STATE =====
        traderData = json.dumps({
            "ve_ema": ve_ema,
            "tick_count": tick_count,
        })

        return result, conversions, traderData