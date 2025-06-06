import asyncio
import json
import os
import time
from datetime import datetime
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
from strategies.StrategyBase import StrategyBase, StrategySignal
from strategies.SB_VOL import StrategySBVOL
from utils.Logger import Logger

class LiveTrader:
    def __init__(self, fyers, lot_size, symbol='NSE:RELIANCE-EQ', interval='5', strategy:StrategyBase=None):
        self.fyers: fyersModel.FyersModel = fyers
        self.symbol = symbol
        self.lot_size = lot_size
        self.interval = interval  # string format as per Fyers: '1', '5', etc.
        self.strategy = strategy
        self.candles = []
        self.active_position = None
        self.current_position = 0
        self.is_started = False

    def on_data(self, message):
        signal = self.strategy.process()
        Logger.log(f"TRADE_SIGNAL: {signal}")
        
        if signal == StrategySignal.NONE:
            return
        
        elif signal == StrategySignal.BUY:
            order_qty = self.lot_size
            if self.current_position < 0:
                order_qty += -1 * self.current_position 
            Logger.log(f"lot_size: {self.lot_size} |current_position: {self.current_position} | order_qty: {order_qty}")
            self.place_order(order_qty)
                
        elif signal == StrategySignal.SELL:
            order_qty = self.lot_size
            if self.current_position > 0:
                order_qty += self.current_position 
            Logger.log(f"lot_size: {self.lot_size} |current_position: {self.current_position} | order_qty: {order_qty}")
            self.place_order(order_qty)
                        
    def place_order(self, order_qty):
        
        side = 1 if order_qty > 0 else -1
        
        order = {
            "symbol": self.symbol,
            "qty": order_qty,
            "type": 2, # market order
            "side": side,
            "productType": "MARGIN",
            "limitPrice": 0,
            "stopPrice": 0,
            "disclosedQty": 0,
            "validity": "DAY",
            "offlineOrder": False,
            "orderTag": "SB_VOL_FYERS_API"
        }
        response = self.fyers.place_order(order)
        
        if response.get("s") == "ok":
            Logger.log(f"Market order {response.get("id")} sent successfully, assuming filled!")
            self.current_position = order_qty
        else:
            Logger.error(f"Order sending failed {response}")

    def start(self):
        Logger.log("Starting Live Trader")
        
        if not self.validate():
            Logger.log("Stoptting Live Trader")
        
        self.is_started = True
        
        
        
    def validate(self) -> bool:
        if self.strategy is None:
            Logger.error("No strategy object provided to live trader")
            return False
        
        if not self.strategy.is_valid:
            Logger.error("Strategy object provided to live trader found invalid")
            return False