#4912
from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import json

class Trader:
    """
    V5 - Ultimate Omni-Spread Sniper 
    Unlocks the true PNL ceiling by aggressively milking the 15-point invisible spreads on BOTH goods, while maintaining the Pepper Root positive trend!
    """
    def __init__(self):
        self.limits = {
            "ASH_COATED_OSMIUM": 80,
            "INTARIAN_PEPPER_ROOT": 80
        }
        self.pepper_ema = None
        
    def run(self, state: TradingState):
        result = {}
        
        # Load EMA out of memory string
        if state.traderData != "":
            try:
                data = json.loads(state.traderData)
                self.pepper_ema = data.get("pepper_ema", None)
            except:
                pass

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            position = state.position.get(product, 0)
            limit = self.limits.get(product, 80)
            
            best_bid = max(order_depth.buy_orders.keys()) if len(order_depth.buy_orders) > 0 else None
            best_ask = min(order_depth.sell_orders.keys()) if len(order_depth.sell_orders) > 0 else None
            
            if best_bid is None or best_ask is None:
                continue
                
            mid = (best_bid + best_ask) / 2.0
            
            if product == "ASH_COATED_OSMIUM":
                fv = 10000
                
                # 1. Take massive, guaranteed, risk-free mispricings
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask <= fv - 3 and position < limit:
                        qty = min(limit - position, -ask_vol)
                        orders.append(Order(product, ask, qty))
                        position += qty
                        
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    if bid >= fv + 3 and position > -limit:
                        qty = min(limit + position, bid_vol)
                        orders.append(Order(product, bid, -qty))
                        position -= qty
                        
                # 2. Hardcoded Spread Sniper (The money printer!)
                # Average trades occur at 9993 and 10008. We place strict limits at 9995 and 10005.
                skew = 0
                if position > 60: skew = -3  # Dump inventory urgently
                elif position > 30: skew = -1 
                elif position < -60: skew = 3
                elif position < -30: skew = 1
                
                my_bid = fv - 5 + skew
                my_ask = fv + 5 + skew
                
                # Protect against negatively crossing a tight spread
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)
                
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))
                    
            elif product == "INTARIAN_PEPPER_ROOT":
                if self.pepper_ema is None:
                    self.pepper_ema = mid
                else:
                    self.pepper_ema = 0.1 * mid + 0.9 * self.pepper_ema
                    
                ema = int(round(self.pepper_ema))
                
                # 1. Market take only if it's genuinely cheap
                for ask, ask_vol in sorted(order_depth.sell_orders.items()):
                    if ask <= ema - 2 and position < limit:
                        qty = min(limit - position, -ask_vol)
                        orders.append(Order(product, ask, qty))
                        position += qty
                        
                for bid, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                    # We ONLY sell on massive spikes to protect our long trend!
                    if bid >= ema + 8 and position > -limit: 
                        qty = min(limit + position, bid_vol)
                        orders.append(Order(product, bid, -qty))
                        position -= qty
                        
                # 2. Asymmetric Trend Sniper
                # Since we want to be heavily LONG, we bid tight and ask wide.
                my_bid = ema - 3 # Competitive bid to quickly accumulate up to 80
                my_ask = ema + 9 # Super high ask; occasionally catches crazy +9 points
                
                if position >= 60:
                    my_bid = ema - 6 # We already have lots, wait for a big dip
                    my_ask = ema + 5 # Lower ask to safely capture an easy 11 point spread!
                
                my_bid = min(my_bid, best_bid + 1)
                my_ask = max(my_ask, best_ask - 1)
                
                if my_bid >= my_ask:
                    my_bid = my_ask - 2
                
                if position < limit:
                    orders.append(Order(product, my_bid, limit - position))
                if position > -limit:
                    orders.append(Order(product, my_ask, -limit - position))
                    
            result[product] = orders
            
        traderData = json.dumps({"pepper_ema": self.pepper_ema})
        conversions = 0
        return result, conversions, traderData
