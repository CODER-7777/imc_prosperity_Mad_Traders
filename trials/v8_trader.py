import json
from datamodel import OrderDepth, TradingState, Order
from typing import List

class Trader:
    """
    The Master Hybrid Algorithm
    - Osmium: Dynamic Order Book Imbalance Market Making.
    - Pepper Root: Persistent EMA Trend Following with Asymmetric Skew.
    """
    def __init__(self):
        # HARD LIMITS: Exactly 20. Do not change this, or the engine will reject your orders.
        self.limits = {
            "ASH_COATED_OSMIUM": 20, 
            "INTARIAN_PEPPER_ROOT": 20
        }
        self.pepper_ema = None
        self.alpha = 0.15  # Smoothing factor for the trend

    def run(self, state: TradingState):
        result = {}
        
        # 1. State Recovery: Pull previous EMA from the engine's JSON memory
        if state.traderData != "":
            try:
                data = json.loads(state.traderData)
                self.pepper_ema = data.get("pepper_ema", None)
            except Exception:
                pass

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            position = state.position.get(product, 0)
            limit = self.limits.get(product, 20)
            
            best_bid = max(order_depth.buy_orders.keys()) if len(order_depth.buy_orders) > 0 else None
            best_ask = min(order_depth.sell_orders.keys()) if len(order_depth.sell_orders) > 0 else None
            
            # Edge case handling: Empty book
            if best_bid is None or best_ask is None:
                continue
                
            mid_price = (best_bid + best_ask) / 2.0
            
            # Calculate live Order Book Imbalance
            total_bid_vol = sum(order_depth.buy_orders.values()) 
            total_ask_vol = sum([-v for v in order_depth.sell_orders.values()])
            
            imbalance = 0.5
            if total_bid_vol + total_ask_vol > 0:
                imbalance = total_bid_vol / (total_bid_vol + total_ask_vol)

            # ---------------------------------------------------------
            # PRODUCT 1: ASH_COATED_OSMIUM (Mean Reverting / Spread Capture)
            # ---------------------------------------------------------
            if product == "ASH_COATED_OSMIUM":
                # Fair Value is dynamically pulled by market pressure
                fv = best_bid + (best_ask - best_bid) * imbalance
                
                # Inventory Skew: Push quotes down if holding too much, up if short
                pos_ratio = position / limit
                spread = best_ask - best_bid
                skew = -pos_ratio * (spread / 2.0)
                
                my_bid = int(round(min(fv - 1 + skew, best_bid + 1)))
                my_ask = int(round(max(fv + 1 + skew, best_ask - 1)))
                
                if my_bid >= my_ask:
                    my_bid = my_ask - 1
                    
                # Market Taking: Snapping guaranteed arbs
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask < my_bid and position < limit:
                        qty = min(limit - position, -ask_vol)
                        orders.append(Order(product, ask, qty))
                        position += qty
                        
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > my_ask and position > -limit:
                        qty = min(limit + position, bid_vol)
                        orders.append(Order(product, bid, -qty))
                        position -= qty
                        
                # Market Making: Resting liquidity
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))

            # ---------------------------------------------------------
            # PRODUCT 2: INTARIAN_PEPPER_ROOT (Directional Trend)
            # ---------------------------------------------------------
            elif product == "INTARIAN_PEPPER_ROOT":
                # Update persistent EMA trend tracker
                if self.pepper_ema is None:
                    self.pepper_ema = mid_price
                else:
                    self.pepper_ema = self.alpha * mid_price + (1 - self.alpha) * self.pepper_ema
                
                # Blend the historical EMA trend with the live order book imbalance
                trend_fv = self.pepper_ema
                imbalance_offset = (imbalance - 0.5) * (best_ask - best_bid)
                dynamic_fv = trend_fv + imbalance_offset
                
                # Asymmetric skew: Maintain an upward bias to capture the historical drift
                skew = -int((position / limit) * 3)
                upward_bias = 1 
                
                my_bid = int(round(min(dynamic_fv - 2 + skew + upward_bias, best_bid + 1)))
                my_ask = int(round(max(dynamic_fv + 2 + skew + upward_bias, best_ask - 1)))
                
                if my_bid >= my_ask:
                    my_bid = my_ask - 1

                # Market Taking
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask < my_bid and position < limit:
                        qty = min(limit - position, -ask_vol)
                        orders.append(Order(product, ask, qty))
                        position += qty
                        
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > my_ask and position > -limit:
                        qty = min(limit + position, bid_vol)
                        orders.append(Order(product, bid, -qty))
                        position -= qty
                        
                # Market Making
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))

            result[product] = orders

        # 2. State Preservation: Pass the updated EMA to the next tick safely
        traderData = json.dumps({"pepper_ema": self.pepper_ema})
        conversions = 0
        
        return result, conversions, traderData