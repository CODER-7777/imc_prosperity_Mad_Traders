"""
IMC Prosperity 4 - Round 5 (FINAL) Strategy
Team: Mad_Traders

TEMPLATE - Fill in when Round 5 starts.

This is the FINAL round. All products from R1-R4 carry forward.
Give it everything.

Workflow:
  1. Analyze round data in data/ folder
  2. Iterate on strategies in the round5/trials branch
  3. Once finalized, copy winning strategy here as strategy.py
  4. Submit on the IMC platform
"""
from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List


class Trader:
    def __init__(self):
        self.limits = {
            "ASH_COATED_OSMIUM": 80,
            "INTARIAN_PEPPER_ROOT": 80,
            # Add ALL products here
        }

    def run(self, state: TradingState):
        result = {}

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            position = state.position.get(product, 0)
            limit = self.limits.get(product, 80)

            best_bid = max(order_depth.buy_orders.keys()) if len(order_depth.buy_orders) > 0 else None
            best_ask = min(order_depth.sell_orders.keys()) if len(order_depth.sell_orders) > 0 else None

            if best_bid is None or best_ask is None:
                continue

            # ========================================
            # CARRY-FORWARD STRATEGIES
            # ========================================

            if product == "ASH_COATED_OSMIUM":
                fv = 10000
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask < fv and position < limit:
                        buy_vol = min(limit - position, -ask_vol)
                        if buy_vol > 0:
                            orders.append(Order(product, ask, buy_vol))
                            position += buy_vol
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fv and position > -limit:
                        sell_vol = max(-limit - position, -bid_vol)
                        if sell_vol < 0:
                            orders.append(Order(product, bid, sell_vol))
                            position += sell_vol
                skew = -int((position / limit) * 3)
                my_bid = fv - 2 + skew
                my_ask = fv + 2 + skew
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))

            elif product == "INTARIAN_PEPPER_ROOT":
                buy_cap = limit - position
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if buy_cap <= 0:
                        break
                    available = -ask_vol
                    qty = min(buy_cap, available)
                    if qty > 0:
                        orders.append(Order(product, ask, qty))
                        buy_cap -= qty
                if buy_cap > 0:
                    orders.append(Order(product, best_bid + 1, buy_cap))

            # ========================================
            # NEW ROUND 5 PRODUCTS — ADD LOGIC BELOW
            # ========================================

            # elif product == "NEW_PRODUCT_NAME":
            #     pass

            result[product] = orders

        conversions = 0
        traderData = ""
        return result, conversions, traderData
