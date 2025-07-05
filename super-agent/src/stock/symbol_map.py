def find_symbol_by_name(name: str) -> str | None:
    """
    Finds the stock symbol for a given Korean stock name.
    
    Args:
        name: The Korean name of the stock (e.g., "삼성전자").

    Returns:
        The stock symbol (e.g., "005930.KS") or None if not found.
    """
    symbol_map = {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "카카오": "035720.KS",
        "NAVER": "035420.KS",
        "LG화학": "051910.KS",
        # Add more mappings as needed
    }
    return symbol_map.get(name)

if __name__ == '__main__':
    # Example usage
    symbol = find_symbol_by_name("삼성전자")
    print(f"'삼성전자'의 종목 코드는 '{symbol}' 입니다.")
    
    symbol = find_symbol_by_name("현대차")
    print(f"'현대차'의 종목 코드는 '{symbol}' 입니다.")
