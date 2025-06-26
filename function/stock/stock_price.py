# stock_price.py
import yfinance as yf
from typing import List, Dict
import math

def get_stock_price(symbol: str) -> List[Dict]:
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="6d")  # 전일 대비 비교 위해 6일

    result = []
    rows = list(data.iterrows())[-5:]  # 최근 5개만

    for i, (date, row) in enumerate(rows):
        today = {
            "date": date.strftime("%Y-%m-%d"),
            "open": row["Open"],
            "close": row["Close"],
            "volume": int(row["Volume"]),
            "change_pct": None,
            "trend": None
        }

        # 전일 대비 종가 비교
        if i > 0:
            prev_close = rows[i - 1][1]["Close"]
            diff = row["Close"] - prev_close
            today["change_pct"] = round((diff / prev_close) * 100, 2)
            today["trend"] = "상승" if diff > 0 else "하락" if diff < 0 else "보합"

        result.append(today)
    return result
