from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List

class Trader:
    """
    V4 - Perfect Sniper Execution
    Optimizes entry prices to squeeze out the absolute maximum PNL.
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
                
            mid_price = (best_bid + best_ask) / 2
                
            if product == "ASH_COATED_OSMIUM":
                fv = 10000
                
                # Market Taking (Only take absolute guaranteed profits)
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask <= fv - 2 and position < limit:
                        buy_vol = min(limit - position, -ask_vol)
                        if buy_vol > 0:
                            orders.append(Order(product, ask, buy_vol))
                            position += buy_vol
                            
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid >= fv + 2 and position > -limit:
                        sell_vol = max(-limit - position, -bid_vol)
                        if sell_vol < 0:
                            orders.append(Order(product, bid, sell_vol))
                            position += sell_vol
                            
                # Market Making
                skew = -int((position / limit) * 3) 
                my_bid = fv - 2 + skew
                my_ask = fv + 2 + skew
                
                # Squeeze the best bounds
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)
                
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))
                    
            elif product == "INTARIAN_PEPPER_ROOT":
                buy_cap = limit - position
                
                # Market take ONLY if the ask is extremely close to the mid price (avoids paying massive spread premiums)
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask > mid_price + 2:  # Don't pay the stupidly high wide ask spread!
                        break
                    if buy_cap <= 0:
                        break
                    available = -ask_vol
                    qty = min(buy_cap, available)
                    if qty > 0:
                        orders.append(Order(product, ask, qty))
                        buy_cap -= qty
                
                # Place SNIPER limit order for the rest slightly above best bid
                # This guarantees we build our 80 position at wholesale prices, not retail prices.
                if buy_cap > 0:
                    orders.append(Order(product, best_bid + 1, buy_cap))
                    
            result[product] = orders
            
        conversions = 0
        traderData = ""
        return result, conversions, traderData
