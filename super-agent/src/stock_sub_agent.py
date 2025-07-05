import os
import json
import openai
from dotenv import load_dotenv

# Import helper functions from other files
from stock.stock_price import get_stock_price
from stock.symbol_map import find_symbol_by_name

# Load environment variables and initialize OpenAI client
load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the function schema for the OpenAI API
get_stock_price_schema = {
    "type": "function",
    "function": {
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
}

def run_stock_analysis(user_prompt: str) -> str:
    """
    Analyzes a user's query about stocks, fetches data using function calling,
    and returns a summarized, user-friendly response.

    Args:
        user_prompt: The user's query about stocks.

    Returns:
        A string containing the summarized stock analysis.
    """
    print(f"Running stock analysis for prompt: '{user_prompt}'")
    
    # 1. Identify the stock name and find its symbol
    symbol = None
    # This list can be expanded or dynamically generated
    known_stocks = ["삼성전자", "SK하이닉스", "카카오", "NAVER", "LG화학"]
    for name in known_stocks:
        if name in user_prompt:
            symbol = find_symbol_by_name(name)
            break

    if not symbol:
        return "죄송합니다, 문의하신 종목을 찾을 수 없습니다. 종목명을 정확히 알려주세요."

    try:
        # 2. First call to OpenAI to trigger the function call
        print(f"Requesting function call for symbol: {symbol}")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an AI that helps users with stock-related questions by calling the necessary functions."},
                {"role": "user", "content": user_prompt}
            ],
            tools=[get_stock_price_schema],
            tool_choice={"type": "function", "function": {"name": "get_stock_price"}}
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls

        if tool_calls:
            # 3. Execute the function call
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            
            if function_name == "get_stock_price":
                # The model might not use the symbol we found, so we force it for accuracy
                args = {"symbol": symbol} 
                print(f"Executing function '{function_name}' with arguments {args}")
                
                # Call the actual function to get stock data
                function_response = get_stock_price(**args)

                # 4. Second call to OpenAI to summarize the results
                print("Summarizing stock data...")
                
                # Prepare messages for the follow-up call
                messages = [
                    {"role": "system", "content": "사용자에게 최근 주가의 추세(상승/하락), 주요 가격(시가, 종가), 변동률, 거래량 등을 친절하고 이해하기 쉽게 요약하여 설명하세요. 예시: '삼성전자는 최근 5일간 전반적으로 상승세를 보였으며, 거래량은 평균 수준을 유지했습니다.'"},
                    {"role": "user", "content": user_prompt},
                    message, # Include the assistant's previous message
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response, ensure_ascii=False),
                    },
                ]

                followup_response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages,
                )
                final_answer = followup_response.choices[0].message.content
                print("Final Answer:", final_answer)
                return final_answer
            
    except Exception as e:
        print(f"An error occurred during stock analysis: {e}")
        return f"주가 분석 중 오류가 발생했습니다: {str(e)}"

    return "죄송합니다, 주가 정보를 조회하는 데 실패했습니다. 다시 시도해 주세요."
