from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment

api_key = "PKNFCY9HB6N8M41LHNS1"
api_secret = "2WobfuriMJCitGk3L5HGBznbHqZw06Y8hGFimthD"
url = "https://paper-api.alpaca.markets"

alpaca_creds = {
    "API_KEY": api_key,
    "API_SECRET": api_secret,
    "PAPER": True
}


class ML_Trader(Strategy): 
    def initialize(self, symbol: str="SPY", cash_at_risk: float=.5):
        self.symbol = symbol
        self.sleeptime = "15S"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url= url, key_id= api_key, secret_key= api_secret)

    def pos_size(self): 
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price)
        return cash, last_price, quantity
    

    def get_sentiment(self):
        today, three_days = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start= three_days, end= today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]

        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment
    
    def get_dates(self): 
        today = self.get_datetime()
        three_days = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days.strftime('%Y-%m-%d')
    

    def on_trading_iteration(self):
        cash, last_price, quantity = self.pos_size()
        probability, sentiment = self.get_sentiment()
    
        if cash > last_price: 
                    if sentiment == "positive" and probability > .999: 
                        if self.last_trade == "sell": 
                            self.sell_all() 
                        order = self.create_order(
                            self.symbol, 
                            quantity, 
                            "buy", 
                            type="market", 
                            take_profit_price=last_price*1.20, 
                            stop_loss_price=last_price*.95
                        )
                        self.submit_order(order) 
                        self.last_trade = "buy"
                    elif sentiment == "negative" and probability > .999: 
                        if self.last_trade == "buy": 
                            self.sell_all() 
                        order = self.create_order(
                            self.symbol, 
                            quantity, 
                            "sell", 
                            type="bracket", 
                            take_profit_price=last_price*.8, 
                            stop_loss_price=last_price*1.05
                        )
                        self.submit_order(order) 
                        self.last_trade = "sell"

        

    


start_date = datetime(2023, 1, 1)
end_date = datetime(2023, 12, 31)

broker = Alpaca(alpaca_creds)
strategy = ML_Trader(name='strat', broker=broker, 
                     parameters={"symbol":"SPY", 
                                 "cash_at_risk":.5})

# strategy.backtest(YahooDataBacktesting, start_date, end_date, parameters={"symbol":"SPY", 
#                                                                         "cash_at_risk":.5})

trader = Trader()
trader.add_strategy(strategy)
trader.run_all()