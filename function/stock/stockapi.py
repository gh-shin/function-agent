import yfinance as yf
import json

# 삼성전자 (005930.KS) 종목
ticker = yf.Ticker("005930.KS")

# 최근 5일간의 주가 데이터 조회
data = ticker.history(period="5d")

# 시가, 종가, 거래량만 추출하여 JSON 형태로 변환
result = []
for date, row in data.iterrows():
    result.append({
        "date": date.strftime("%Y-%m-%d"),
        "open": row["Open"],
        "close": row["Close"],
        "volume": int(row["Volume"])
    })

# JSON 문자열 출력
json_output = json.dumps(result, indent=2, ensure_ascii=False)
print(json_output)
