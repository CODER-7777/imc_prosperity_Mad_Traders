from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import json

class Trader:
    """
    Highly Optimized IMC Prosperity Algorithm
    Fixes the order rejection issues by dynamically mapping the correct limits.
    """
    def __init__(self):
        # The correct position limit for Round 1 items is typically 20. 
        # Exceeding this causes the exchange to reject orders (which causes low PNL!)
        self.limits = {
            "ASH_COATED_OSMIUM": 20,
            "INTARIAN_PEPPER_ROOT": 20
        }
        self.pepper_ema = None
        self.alpha = 0.2
        
    def run(self, state: TradingState):
        result = {}
        
        # We retrieve our historical EMA from traderData so it doesn't reset every tick!
        if state.traderData != "":
            try:
                data = json.loads(state.traderData)
                self.pepper_ema = data.get("pepper_ema", None)
            except:
                pass
                
        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            position = state.position.get(product, 0)
            limit = self.limits.get(product, 20)
            
            best_bid = max(order_depth.buy_orders.keys()) if len(order_depth.buy_orders) > 0 else None
            best_ask = min(order_depth.sell_orders.keys()) if len(order_depth.sell_orders) > 0 else None
            
            if best_bid is None or best_ask is None:
                continue
                
            mid_price = (best_bid + best_ask) / 2
            
            if product == "ASH_COATED_OSMIUM":
                fv = 10000
                
                # ---- PHASE 1: MARKET TAKING ----
                # Sweep asks below fair value
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask < fv and position < limit:
                        buy_vol = min(limit - position, -ask_vol)
                        if buy_vol > 0:
                            orders.append(Order(product, ask, buy_vol))
                            position += buy_vol
                            
                # Sweep bids above fair value
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fv and position > -limit:
                        sell_vol = max(-limit - position, -bid_vol)
                        if sell_vol < 0:
                            orders.append(Order(product, bid, sell_vol))
                            position += sell_vol
                            
                # ---- PHASE 2: MARKET MAKING ----
                # Skew pricing based on inventory to safely offload
                skew = -int((position / limit) * 2) 
                my_bid = fv - 2 + skew
                my_ask = fv + 2 + skew
                
                # Bounding so we don't cross the spread accidentally
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)
                
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))
                    
            elif product == "INTARIAN_PEPPER_ROOT":
                if self.pepper_ema is None:
                    self.pepper_ema = mid_price
                else:
                    self.pepper_ema = self.alpha * mid_price + (1 - self.alpha) * self.pepper_ema
                    
                fv = int(round(self.pepper_ema))
                
                # ---- PHASE 1: MARKET TAKING ----
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask < fv - 1 and position < limit:
                        buy_vol = min(limit - position, -ask_vol)
                        if buy_vol > 0:
                            orders.append(Order(product, ask, buy_vol))
                            position += buy_vol
                            
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fv + 1 and position > -limit:
                        sell_vol = max(-limit - position, -bid_vol)
                        if sell_vol < 0:
                            orders.append(Order(product, bid, sell_vol))
                            position += sell_vol
                            
                # ---- PHASE 2: TREND-SKEWED MARKET MAKING ----
                skew = -int((position / limit) * 3) 
                upward_bias = 1  # Add upward bias because this asset heavily trends up!
                
                my_bid = fv - 2 + skew + upward_bias
                my_ask = fv + 2 + skew + upward_bias
                
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)
                
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))
            
            result[product] = orders
            
        # Save EMA into traderData to persist across ticks
        traderData = json.dumps({"pepper_ema": self.pepper_ema})
        conversions = 0
        return result, conversions, traderData
