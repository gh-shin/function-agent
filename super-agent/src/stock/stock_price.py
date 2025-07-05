import json
from datetime import datetime, timedelta

def get_stock_price(symbol: str) -> dict:
    """
    Fetches the last 5 days of stock price information for a given symbol.
    In a real application, this would call a financial data API.
    This is a dummy implementation for demonstration.

    Args:
        symbol: The stock symbol (e.g., "005930.KS").

    Returns:
        A dictionary containing the stock data.
    """
    print(f"Fetching stock price for symbol: {symbol}")
    # Dummy data for demonstration
    end_date = datetime.now()
    stock_data = {
        "symbol": symbol,
        "data": []
    }
    
    # Generate 5 days of fake data
    for i in range(5):
        date = end_date - timedelta(days=i)
        day_data = {
            "date": date.strftime("%Y-%m-%d"),
            "open": 75000 + (i * 100),
            "high": 76000 + (i * 100),
            "low": 74500 + (i * 100),
            "close": 75500 + (i * 150),
            "volume": 15000000 - (i * 500000)
        }
        stock_data["data"].insert(0, day_data) # Insert at the beginning to have dates in ascending order

    return stock_data

if __name__ == '__main__':
    # Example usage
    samsung_data = get_stock_price("005930.KS")
    print(json.dumps(samsung_data, indent=2, ensure_ascii=False))
