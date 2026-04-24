#3166
from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List

class Trader:
    """
    V6 - General Dynamic Market Maker
    No hardcoded fair values, no magic numbers, zero overfitting.
    Dynamically adjusts to ANY spread, ANY trend, and ANY asset by using Order Book Imbalance and precise Inventory Skewing.
    """
    def __init__(self):
        self.limits = {
            "ASH_COATED_OSMIUM": 80,
            "INTARIAN_PEPPER_ROOT": 80
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
                
            # 1. Order Book Imbalance Fair Value
            # Standard General Algo: Instead of a blind average, weight it by market volume pressure!
            total_bid_vol = sum(order_depth.buy_orders.values()) 
            total_ask_vol = sum([-v for v in order_depth.sell_orders.values()])
            
            if total_bid_vol + total_ask_vol > 0:
                imbalance = total_bid_vol / (total_bid_vol + total_ask_vol)
                fv = best_bid + (best_ask - best_bid) * imbalance
            else:
                fv = (best_bid + best_ask) / 2.0
                
            # 2. Risk (Inventory) Management Skew
            # Normalized position to exactly [-1, 1]
            pos_ratio = position / limit
            
            # The more we own, the more we lower our prices to encourage selling and discourage buying
            spread = best_ask - best_bid
            skew = -pos_ratio * (spread / 2.0)
            
            # 3. Dynamic Bounding & Pricing
            target_bid = fv - 1 + skew
            target_ask = fv + 1 + skew
            
            # Cap our orders strictly just inside or at the best market levels
            my_bid = int(round(min(target_bid, best_bid + 1)))
            my_ask = int(round(max(target_ask, best_ask - 1)))
            
            # Safety checks to prevent accidentally crossing our own spread
            if my_bid >= my_ask:
                my_bid = my_ask - 1
                
            # 4. Market Taking (Arb/Liquidity Snapping)
            # Sweep any orders literally strictly better than our FV + Skew bounds!
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
                    
            # 5. Market Making
            # Output resting liquidity using entirely dynamic bounds based purely on real-time data
            if position < limit:
                buy_qty = limit - position
                orders.append(Order(product, my_bid, buy_qty))
            if position > -limit:
                sell_qty = -limit - position
                orders.append(Order(product, my_ask, sell_qty))
                
            result[product] = orders
            
        return result, 0, ""
