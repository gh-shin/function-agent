# symbol_map_crypto.py
crypto_code_map = {
    "비트코인": "BTCUSDT",
    "비트": "BTCUSDT",
    "BTC": "BTCUSDT",
    "이더리움": "ETHUSDT",
    "이더": "ETHUSDT",
    "ETH": "ETHUSDT",
    "리플": "XRPUSDT",
    "XRP": "XRPUSDT",
    "솔라나": "SOLUSDT",
    "SOL": "SOLUSDT",
    # 필요시 추가
}

def find_symbol_by_name(name: str) -> str | None:
    return crypto_code_map.get(name.upper(), crypto_code_map.get(name)) 