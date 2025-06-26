# main.py
import os
import json
import asyncio
import openai
from dotenv import load_dotenv
from stock_price import get_stock_price
from symbol_map import find_symbol_by_name

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Function schema
get_stock_price_schema = {
    "name": "get_stock_price",
    "description": "특정 종목의 최근 5일간 주가 정보를 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "조회할 종목 코드 (예: '005930.KS')"
            }
        },
        "required": ["symbol"]
    }
}

async def main():
    user_prompt = "삼성전자 최근 주가 어때? 시가랑 거래량도 알려줘."

    # 종목명 → 코드 매핑
    symbol = None
    for name in ["삼성전자", "SK하이닉스", "카카오", "NAVER", "LG화학"]:
        if name in user_prompt:
            symbol = find_symbol_by_name(name)
            break

    if not symbol:
        print("⛔ 종목명을 찾을 수 없습니다.")
        return

    # GPT에 function call 실행
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "사용자의 주식 질문에 응답하는 AI입니다."},
            {"role": "user", "content": user_prompt}
        ],
        functions=[get_stock_price_schema],
        function_call={"name": "get_stock_price", "arguments": json.dumps({"symbol": symbol})}
    )

    message = response.choices[0].message

    if message.function_call:
        args = json.loads(message.function_call.arguments)
        result = get_stock_price(**args)

        # main.py (요약만)
        # 기존 코드 그대로 유지하고 아래 부분만 보강

        followup = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": user_prompt},
                message.model_dump(),
                {
                    "role": "function",
                    "name": "get_stock_price",
                    "content": json.dumps(result, ensure_ascii=False),
                },
                {
                    "role": "system",
                    "content": "사용자에게 최근 주가의 추세(상승/하락), 변동률, 거래량 등을 요약하여 설명하세요. 예시: '삼성전자는 5일간 하락세이며, 거래량은 평균적으로 유지되었습니다.'",
                },
            ],
        )
        print("📊 GPT 최종 응답:")
        print(followup.choices[0].message.content)

    else:
        print("GPT가 함수 호출을 제안하지 않았습니다.")

if __name__ == "__main__":
    asyncio.run(main())
