"""
Boilerplate Competitor Class
----------------------------

Instructions for Participants:
1. Do not import external libraries beyond what's provided.
2. Focus on implementing the `strategy()` method with your trading logic.
3. Use the provided methods to interact with the exchange:
   - self.create_limit_order(price, size, side, symbol) -> order_id if succesfully placed in order book or None
   - self.create_market_order(size, side, symbol) -> order_id if succesfully placed in order book or None
   - self.remove_order(order_id, symbol) -> bool
   - self.get_order_book_snapshot(symbol) -> dict
   - self.get_balance -> float
   - self.get_portfolio -> dict

   
Happy Trading!
"""

from typing import Optional, List, Dict
import numpy as np

from Participant import Participant

class CompetitorBoilerplate(Participant):
    def __init__(self, 
                 participant_id: str,
                 order_book_manager=None,
                 order_queue_manager=None,
                 balance: float = 100000.0):
        """
        Initializes the competitor with default strategy parameters.
        
        :param participant_id: Unique ID for the competitor.
        :param order_book_manager: Reference to the OrderBookManager.
        :param order_queue_manager: Reference to the OrderQueueManager.
        :param balance: Starting balance for the competitor.
        """
        super().__init__(
            participant_id=participant_id,
            balance=balance,
            order_book_manager=order_book_manager,
            order_queue_manager=order_queue_manager
        )

        # Strategy parameters (fixed defaults)
        self.symbols: List[str] = ["NVR", "CPMD", "MFH", "ANG", "TVW"]
        self.volatility_memory = {symbol: 0.0 for symbol in self.symbols}
        self.mid_price_memory = {symbol: None for symbol in self.symbols}
        self.ema_memory = {symbol: None for symbol in self.symbols}
        self.alpha = 0.1

    def get_mid_price(self, symbol):
        snapshot = self.get_order_book_snapshot(symbol)
        if not snapshot:
            return None

        best_bid = snapshot.get("bids", [])
        best_ask = snapshot.get("asks", [])

        if not best_bid or not best_ask:
            return None
        
        return (best_bid[0][0] + best_ask[0][0]) / 2

    def calculate_volatility(self, symbol, window=10):
        mid_price = self.get_mid_price(symbol)
        if mid_price is None:
            return self.volatility_memory[symbol]

        if self.mid_price_memory[symbol] is None:
            self.mid_price_memory[symbol] = mid_price
            return 0.0

        price_change = abs(mid_price - self.mid_price_memory[symbol])
        self.volatility_memory[symbol] = price_change  # Store latest price change
        self.mid_price_memory[symbol] = mid_price

        return price_change

    def calculate_order_book_imbalance(self, symbol):
        snapshot = self.get_order_book_snapshot(symbol)
        if not snapshot:
            return 0

        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])

        total_bid_size = sum([b[1] for b in bids[:5]])  # Sum of top 5 bid sizes
        total_ask_size = sum([a[1] for a in asks[:5]])  # Sum of top 5 ask sizes

        if total_bid_size + total_ask_size == 0:
            return 0

        return (total_bid_size - total_ask_size) / (total_bid_size + total_ask_size)

    def adaptive_pennying_strategy(self, symbol):
        snapshot = self.get_order_book_snapshot(symbol)
        if not snapshot:
            return

        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])

        if not bids or not asks:
            return

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = self.get_mid_price(symbol)
        volatility = self.calculate_volatility(symbol)
        imbalance = self.calculate_order_book_imbalance(symbol)

        if imbalance > 0:  # buy-side pressure
            penny_bid_levels = [best_bid + 0.02, best_bid + 0.03]
            penny_ask_levels = [best_ask - 0.01]
        elif imbalance < 0:  # sell-side pressure
            penny_bid_levels = [best_bid + 0.01]
            penny_ask_levels = [best_ask - 0.02, best_ask - 0.03]
        else:
            penny_bid_levels = [best_bid + 0.01, best_bid + 0.02]
            penny_ask_levels = [best_ask - 0.01, best_ask - 0.02]

        for bid_price in penny_bid_levels:
            self.create_limit_order(price=bid_price, size=5, side="buy", symbol=symbol)
        for ask_price in penny_ask_levels:
            self.create_limit_order(price=ask_price, size=5, side="sell", symbol=symbol)

    def volatility_adaptive_levels(self, symbol):
        snapshot = self.get_order_book_snapshot(symbol)
        if not snapshot:
            return
        
        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])

        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None

        if best_bid is None or best_ask is None:
            return
    
        volatility = self.calculate_volatility(symbol)

        base_level_distance = 0.05
        level_factor = 1 + (volatility * 0.1)
        level_distance = base_level_distance * level_factor

        deep_bid_levels = [best_bid - level_distance * i for i in range(1, 4)]
        deep_ask_levels = [best_ask + level_distance * i for i in range(1, 4)]

        for bid_price in deep_bid_levels:
            self.create_limit_order(price=bid_price, size=10, side="buy", symbol=symbol)
        for ask_price in deep_ask_levels:
            self.create_limit_order(price=ask_price, size=10, side="sell", symbol=symbol)

    # adjust order size based off volatility
    def smart_order_sizing(self, symbol):
        volatility = self.calculate_volatility(symbol)
        base_order_size = 10

        if volatility < 0.5:
            order_size = base_order_size * 1.5
        elif volatility > 2.0:
            order_size = base_order_size * 0.5
        else:
            order_size = base_order_size

        return max(1, int(order_size))

    def detect_large_orders(self, symbol):
        snapshot = self.get_order_book_snapshot(symbol)
        if not snapshot:
            return

        bids = snapshot.get("bids", [])
        asks = snapshot.get("asks", [])

        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None

        if best_bid is None or best_ask is None:
            return

        large_order_threshold = 50

        if bids and bids[0][1] > large_order_threshold:
            self.create_limit_order(price=bids[0][0] + 0.01, size=5, side="buy", symbol=symbol)
        if asks and asks[0][1] > large_order_threshold:
            self.create_limit_order(price=asks[0][0] - 0.01, size=5, side="sell", symbol=symbol)

    def strategy(self):
        for symbol in self.symbols:
            self.adaptive_pennying_strategy(symbol)
            self.volatility_adaptive_levels(symbol)
            self.detect_large_orders(symbol)