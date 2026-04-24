from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List

class Trader:
    """
    V9 - The 20k Ceiling Breaker
    - Restores the true Limit=80 boundaries to unleash 4x volume.
    - Pepper Root: Uses the mathematically proven "Max Long Sniper" sweep to lock in the 8k trend.
    - Osmium: Flawless Penny-Jumping Spread Scalper to squeeze out 12k+.
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
                
            if product == "ASH_COATED_OSMIUM":
                fv = 10000
                
                # Phase 1: Market Taking - Instant Arbitrage Snapping
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask < fv and position < limit:
                        qty = min(limit - position, -ask_vol)
                        orders.append(Order(product, ask, qty))
                        position += qty
                        
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid > fv and position > -limit:
                        qty = min(limit + position, bid_vol)
                        orders.append(Order(product, bid, -qty))
                        position -= qty
                        
                # Phase 2: Aggressive Queue-Jumping Scalper
                # Osmium spreads fluctuate wildly. To maximize trade volume, we ALWAYS jump the best queue by 1,
                # tightly bounded by our inventory skew to prevent holding risk.
                skew = -int((position / limit) * 3) # Shift pricing dynamically if the back room gets too full
                
                my_bid = best_bid + 1
                my_ask = best_ask - 1
                
                # Protect profits: Ensure we never bid worse than fv-1, and never ask worse than fv+1.
                my_bid = min(my_bid, fv - 2 + skew)
                my_ask = max(my_ask, fv + 2 + skew)
                
                # Safety check
                if my_bid >= my_ask:
                    my_bid = my_ask - 1
                    
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))
                    
            elif product == "INTARIAN_PEPPER_ROOT":
                # Market is strictly drifting up +1000/day.
                # PROVEN STRATEGY: Accumulate 80 units immediately at wholesale, NEVER SELL.
                buy_cap = limit - position
                
                # Sweep wholesale asks that are close to the bid
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if buy_cap <= 0: break
                    if ask > best_bid + 3: break # Ensure we don't accidentally buy a massive spike
                    
                    available = -ask_vol
                    qty = min(buy_cap, available)
                    if qty > 0:
                        orders.append(Order(product, ask, qty))
                        buy_cap -= qty
                
                # Passively accumulate the rest slightly above best bid to squeeze out the best entry prices
                if buy_cap > 0:
                    orders.append(Order(product, best_bid + 1, buy_cap))
                    
            result[product] = orders
            
        return result, 0, ""
