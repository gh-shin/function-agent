from openai import OpenAI

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime, timedelta
load_dotenv()
from dateutil.parser import parse as parse_datetime 
from tools import mail_agent, search_agent
# --- 전문가 에이전트(도구) 생성 및 등록 ---

tools_for_super_agent = [mail_agent, 
                         search_agent,
                         ]

def create_super_agent(today_str: str):
    """
    여러 전문가 에이전트를 도구로 사용하는 최상위 라우터 에이전트를 생성합니다.
    """
    
    # --- 슈퍼 에이전트 프롬프트 및 LLM 설정 ---
    
    # 슈퍼 에이전트에게 자신의 역할과 사용할 수 있는 전문가들에 대해 명확히 알려줍니다.
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a master AI assistant (super agent). 당신은 사용자의 복잡한 요청을 분석하여, 각 분야의 전문가 어시스턴트에게 작업을 정확히 분배하는 역할을 합니다.
        사용 가능한 전문가 목록은 다음과 같습니다:
        - email_management_specialist: 이메일 관련 모든 작업을 처리하는 전문가.
        - web_search_specialist: 웹 검색 관련 모든 작업을 처리하는 전문가.
        
        오늘 날짜는 {today}입니다."""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

    # --- 슈퍼 에이전트 생성 및 반환 ---
    agent = create_openai_functions_agent(llm, tools_for_super_agent, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools_for_super_agent, verbose=True)
    
    return agent_executor


if __name__ == "__main__":
    load_dotenv()
    today_str = datetime.now().strftime("%Y-%m-%d")
    super_agent = create_super_agent(today_str = today_str)
    
    # 두 전문가의 협업이 필요한 복합 쿼리
    query = "최신 AI 기술 동향에 대해 TechCrunch에서 검색해서, 그 내용을 바탕으로 우리 팀에게 공유할 메일 초안을 작성해줘. 받는 사람은 'dev_team@mycompany.com' 이야."
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n==================================================")
    print(f"[사용자 쿼리]: {query}")
    print(f"==================================================")
    
    result = super_agent.invoke({
        "input": query,
        "today": today_str,
        "chat_history": []
    })
    
    ai_response = result['output']
    print(f"\n[슈퍼 에이전트 최종 답변]: {ai_response}")





# # --- 멀티턴 대화를 위한 메인 실행 블록 ---
# if __name__ == "__main__":
#     load_dotenv()
#     today_str = datetime.now().strftime("%Y-%m-%d")
#     super_agent = create_super_agent(today_str = today_str)
#     chat_history = []
    
#     print("AI 이메일 어시스턴트입니다. 무엇을 도와드릴까요? (종료하려면 'exit' 또는 '종료'를 입력하세요)")

#     while True:
#         try:
#             user_input = input("\nYou: ")
            
#             if user_input.lower() in ["exit", "종료"]:
#                 print("어시스턴트를 종료합니다.")
#                 break

#             result = super_agent.invoke({
#                 "input": user_input,
#                 "today": today_str,
#                 "chat_history": chat_history 
#             })
            
#             ai_response = result['output']
#             print(f"\nAI: {ai_response}")

#             chat_history.append(HumanMessage(content=user_input))
#             chat_history.append(AIMessage(content=ai_response))

#             if len(chat_history) > 10: # 최근 5번의 대화만 기억
#                 chat_history = chat_history[-10:]

#         except Exception as e:
#             print(f"오류가 발생했습니다: {e}")
