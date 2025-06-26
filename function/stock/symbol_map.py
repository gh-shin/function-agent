# symbol_map.py
stock_code_map = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "카카오": "035720.KQ",
    "NAVER": "035420.KQ",
    "LG화학": "051910.KS",
    # 필요한 종목 계속 추가 가능
}

def find_symbol_by_name(name: str) -> str | None:
    return stock_code_map.get(name)
