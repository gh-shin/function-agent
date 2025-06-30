import os
import json
import asyncio
import openai
from dotenv import load_dotenv
from Binance_test import get_crypto_analysis, get_pi_cycle_analysis
from symbol_map_crypto import find_symbol_by_name

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function schema 예시
get_crypto_analysis_schema = {
    "name": "get_crypto_analysis",
    "description": "특정 코인의 최근 가격, 변동성, 거래량 등 주요 지표를 조회합니다.",
    "parameters": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "코인 심볼 (예: 'BTCUSDT')"},
            "interval": {"type": "string", "description": "캔들 간격 (예: '1h', '1d')"},
            "limit": {"type": "integer", "description": "조회할 데이터 개수 (예: 24)"}
        },
        "required": ["symbol", "interval", "limit"]
    }
}

async def main():
    user_prompt = "비트코인 1시간 변동성, 거래량, 시가총액 알려줘. 그리고 pi cycle top 신호도 분석해줘."

    # 코인명 추출 및 심볼 매핑 (간단 예시)
    symbol = None
    for name in ["비트코인", "BTC", "이더리움", "ETH", "리플", "XRP", "솔라나", "SOL"]:
        if name in user_prompt:
            symbol = find_symbol_by_name(name)
            break
    if not symbol:
        print("❌ 코인명을 찾을 수 없습니다.")
        return
    interval = "1h" if "1시간" in user_prompt else "1d"
    limit = 24 if interval == "1h" else 30

    # LLM function call
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "암호화폐 데이터 분석 AI입니다."},
            {"role": "user", "content": user_prompt}
        ],
        functions=[get_crypto_analysis_schema],
        function_call={"name": "get_crypto_analysis", "arguments": json.dumps({"symbol": symbol, "interval": interval, "limit": limit})}
    )

    message = response.choices[0].message

    if message.function_call:
        args = json.loads(message.function_call.arguments)
        df, result = get_crypto_analysis(**args)
        # pi cycle top도 추가로 호출
        df_pi, pi_result = get_pi_cycle_analysis(symbol, "1d", 500)

        followup = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": user_prompt},
                message.model_dump(),
                {
                    "role": "function",
                    "name": "get_crypto_analysis",
                    "content": json.dumps(result, ensure_ascii=False),
                },
                {
                    "role": "function",
                    "name": "get_pi_cycle_analysis",
                    "content": json.dumps(pi_result, ensure_ascii=False),
                },
                {
                    "role": "system",
                    "content": "사용자에게 최근 코인 가격, 변동성, 거래량, pi cycle top 신호 등을 요약해서 설명하세요. pi cycle top 신호가 과열이면 경고 메시지도 추가하세요."
                },
            ],
        )
        print("GPT 최종 응답:")
        print(followup.choices[0].message.content)
    else:
        print("GPT가 함수 호출을 제안하지 않았습니다.")

if __name__ == "__main__":
    asyncio.run(main()) 