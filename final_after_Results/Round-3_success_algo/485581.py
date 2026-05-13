from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List


class Trader:
    LIMITS = {
        "HYDROGEL_PACK": 80,
        "VELVETFRUIT_EXTRACT": 80,
        "VEV_5300": 80,
        "VEV_5400": 80,
    }

    def run(self, state: TradingState):
        orders: Dict[str, List[Order]] = {product: [] for product in state.order_depths}

        self.take_only(
            product="HYDROGEL_PACK",
            fair=9990.0,
            edge=30.0,
            lot=10,
            state=state,
            orders=orders,
        )

        self.take_only(
            product="VELVETFRUIT_EXTRACT",
            fair=5255.0,
            edge=10.0,
            lot=10,
            state=state,
            orders=orders,
        )

        spot = self.mid_price(state.order_depths.get("VELVETFRUIT_EXTRACT"))
        if spot is not None:
            self.take_only(
                product="VEV_5300",
                fair=max(0.0, spot - 5300.0) + 47.0,
                edge=5.0,
                lot=10,
                state=state,
                orders=orders,
            )
            self.take_only(
                product="VEV_5400",
                fair=max(0.0, spot - 5400.0) + 16.5,
                edge=2.0,
                lot=10,
                state=state,
                orders=orders,
            )

        return orders, 0, ""

    def take_only(
        self,
        product: str,
        fair: float,
        edge: float,
        lot: int,
        state: TradingState,
        orders: Dict[str, List[Order]],
    ) -> None:
        depth = state.order_depths.get(product)
        if depth is None or (not depth.buy_orders and not depth.sell_orders):
            return

        position = state.position.get(product, 0)
        limit = self.LIMITS[product]

        if depth.sell_orders:
            best_ask = min(depth.sell_orders)
            ask_volume = -depth.sell_orders[best_ask]
            if best_ask <= fair - edge and position < limit:
                qty = min(ask_volume, limit - position, lot)
                if qty > 0:
                    orders[product].append(Order(product, best_ask, qty))
                    position += qty

        if depth.buy_orders:
            best_bid = max(depth.buy_orders)
            bid_volume = depth.buy_orders[best_bid]
            if best_bid >= fair + edge and position > -limit:
                qty = min(bid_volume, limit + position, lot)
                if qty > 0:
                    orders[product].append(Order(product, best_bid, -qty))

    def mid_price(self, depth: OrderDepth):
        if depth is None or not depth.buy_orders or not depth.sell_orders:
            return None
        return (max(depth.buy_orders) + min(depth.sell_orders)) / 2.0