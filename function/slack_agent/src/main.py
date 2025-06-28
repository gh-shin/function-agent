import os
import requests
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime, timedelta
load_dotenv()
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

@tool
def send_slack_notification(message: str, notification_type: str = "info"):
    """
    사용자에게 중요한 정보를 전달하거나 작업 상태를 알리기 위해 Slack으로 알림 메시지를 보냅니다.
    이 도구는 AI가 자신의 작업 진행 상황(시작, 완료, 실패)을 사용자에게 능동적으로 보고해야 할 때 사용합니다.
    - message (str): 슬랙으로 보낼 핵심 메시지 내용.
    - notification_type (str, optional): 알림의 종류. 'info'(정보, 기본값), 'success'(성공), 'warning'(경고), 'error'(오류) 중 하나를 선택할 수 있습니다.
    """
    print(f"--- 툴 호출: send_slack_notification ---")
    
    if not SLACK_WEBHOOK_URL:
        # LLM에게 실패 원인을 명확히 알려주기 위해 문자열을 반환합니다.
        return "슬랙 알림 실패: Webhook URL이 설정되지 않았습니다."

    # 알림 종류에 따라 색상과 제목을 다르게 설정
    color_map = {
        "success": "#36a64f", # 초록색
        "info": "#439fe0",    # 파란색
        "warning": "#f2c744", # 노란색
        "error": "#d50200"    # 빨간색
    }
    pretext_map = {
        "success": "✅ 작업 완료",
        "info": "🔔 AI Assistant 알림",
        "warning": "⚠️ 주의",
        "error": "🔥 오류 발생"
    }
    
    color = color_map.get(notification_type.lower(), color_map['info'])
    pretext = pretext_map.get(notification_type.lower(), pretext_map['info'])

    try:
        payload = {
            "attachments": [{"color": color, "pretext": pretext, "text": message}]
        }
        response = requests.post(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 200:
            return "성공적으로 슬랙 알림을 보냈습니다."
        else:
            # LLM이 실패 원인을 알 수 있도록 상세한 에러 메시지를 반환합니다.
            return f"슬랙 알림 전송 실패: {response.status_code}, {response.text}"
            
    except Exception as e:
        return f"슬랙 알림 중 예외 발생: {e}"
    


# 프롬프트에 AI가 이 Tool을 언제 사용해야 할지 힌트를 줍니다.


prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant. 현재 날짜는 {today} 입니다. 사용자의 요청을 분석하여 적절한 도구를 사용하세요."),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 에이전트와 실행기 생성 (기존과 동일)
llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
tools = [send_slack_notification]
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)



if __name__ == "__main__":
    
    user_request = "너는 방금 중요한 이메일을 하나 발송했어. 이걸 slack에 알림으로 보내주면 좋겠어."
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n==================================================")
    print(f"[사용자 쿼리]: {user_request}")
    print(f"==================================================")
    
    # 에이전트 실행
    result = agent_executor.invoke({
        "input": user_request,
        "today": today_str
    })
    
    
    print(f"\n[AI 최종 답변]: {result['output']}")