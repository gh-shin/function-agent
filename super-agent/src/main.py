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
    now = datetime.now().strftime("%Y-%m-%d")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""You are a master AI assistant (super agent). 당신은 사용자의 복잡한 요청을 분석하여, 각 분야의 전문가 어시스턴트에게 작업을 정확히 분배하는 역할을 합니다.
        사용 가능한 전문가 목록은 다음과 같습니다:
        - email_management_specialist: 이메일 관련 모든 작업을 처리하는 전문가.
        - web_search_specialist: 웹 검색 관련 모든 작업을 처리하는 전문가.
        
        오늘 날짜는 {now} 입니다다
        """,
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

    agent = create_openai_functions_agent(llm, orchestrator_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=orchestrator_tools, verbose=True)

    return agent_executor


if __name__ == "__main__":
    load_dotenv()
    today_str = datetime.now().strftime("%Y-%m-%d")
    super_agent = create_super_agent(today_str=today_str)

    # 두 전문가의 협업이 필요한 복합 쿼리
    query = "최신 AI 기술 동향에 대해 TechCrunch에서 검색해서, 그 내용을 바탕으로 우리 팀에게 공유할 메일 초안을 작성해줘. 받는 사람은 'dev_team@mycompany.com' 이야."
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n==================================================")
    print(f"[사용자 쿼리]: {query}")
    print(f"==================================================")

    result = super_agent.invoke(
        {"input": query, "today": today_str, "chat_history": []}
    )

    ai_response = result["output"]
    print(f"\n[슈퍼 에이전트 최종 답변]: {ai_response}")


# # --- 전문가 에이전트(도구) 생성 및 등록 ---

# # 1. 이메일 전문가 에이전트를 생성합니다.
# mail_agent_executor = create_mail_agent_executor()

# # 2. 검색 전문가 에이전트를 생성합니다.
# search_agent_executor = create_search_agent_executor()

# # 3. 생성된 각 전문가 에이전트를 'Tool' 객체로 감싸 슈퍼 에이전트가 사용할 도구 목록을 만듭니다.
# tools_for_super_agent = [
#     Tool(
#         name="email_management_specialist",
#         # 상위 에이전트가 이 도구를 호출하면, 람다 함수가 실행됩니다.
#         # user_input에는 상위 에이전트가 판단한 작업 내용(문자열)이 들어옵니다.
#         # 이 문자열을 하위 에이전트가 필요로 하는 {"input": ..., "today": ...} 딕셔너리 형태로 변환하여 invoke 해줍니다.
#         func=lambda user_input: mail_agent_executor.invoke(
#             {
#                 "input": user_input,
#                 "today": today_str,  # create_super_agent 함수가 받은 today_str 값을 주입합니다.
#             }
#         ),
#         # 이 설명은 슈퍼 에이전트(LLM)가 어떤 도구를 선택할지 결정하는 데 사용하는 가장 중요한 정보입니다.
#         description="""사용자의 Gmail 계정과 관련된 작업을 처리하는 이메일 전문가입니다.
#         메일 검색, 초안 작성, 특정인과의 대화 요약 등의 기능을 수행합니다.
#         '메일', '이메일', '편지', '초안', '답장'과 같은 키워드가 있을 때 사용하세요.""",
#     ),
#     Tool(
#         name="web_search_specialist",
#         # 이메일 전문가와 동일한 패턴으로, 하위 검색 에이전트가 필요로 하는
#         # 모든 변수(input, today)를 포함한 딕셔너리를 만들어 전달합니다.
#         func=lambda user_input: search_agent_executor.invoke(
#             {
#                 "input": user_input,
#                 "today": today_str,  # create_super_agent 함수가 받은 today_str 값을 주입합니다.
#             }
#         ),
#         description="""웹 검색이 필요할 때 사용하는 전문 검색 도우미입니다.
#         일반적인 질문 답변, 특정 기술 뉴스 사이트(TechCrunch, The Verge) 검색,
#         또는 주제 관련 링크 목록 찾기 등 다양한 검색 작업을 수행할 수 있습니다.
#         '검색해줘', '알려줘', '뉴스', '링크 찾아줘', '최신 동향'과 같은 요청에 사용하세요.""",
#     ),
# ]


# def create_super_agent(today_str: str):
#     """
#     여러 전문가 에이전트를 도구로 사용하는 최상위 라우터 에이전트를 생성합니다.
#     """

#     # --- 슈퍼 에이전트 프롬프트 및 LLM 설정 ---

#     # 슈퍼 에이전트에게 자신의 역할과 사용할 수 있는 전문가들에 대해 명확히 알려줍니다.
#     prompt = ChatPromptTemplate.from_messages(
#         [
#             (
#                 "system",
#                 """You are a master AI assistant (super agent). 당신은 사용자의 복잡한 요청을 분석하여, 각 분야의 전문가 어시스턴트에게 작업을 정확히 분배하는 역할을 합니다.
#         사용 가능한 전문가 목록은 다음과 같습니다:
#         - email_management_specialist: 이메일 관련 모든 작업을 처리하는 전문가.
#         - web_search_specialist: 웹 검색 관련 모든 작업을 처리하는 전문가.

#         오늘 날짜는 {today}입니다.""",
#             ),
#             MessagesPlaceholder(variable_name="chat_history", optional=True),
#             ("human", "{input}"),
#             MessagesPlaceholder(variable_name="agent_scratchpad"),
#         ]
#     )

#     llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

#     # --- 슈퍼 에이전트 생성 및 반환 ---
#     agent = create_openai_functions_agent(llm, tools_for_super_agent, prompt)
#     agent_executor = AgentExecutor(
#         agent=agent, tools=tools_for_super_agent, verbose=True
#     )

#     return agent_executor


# if __name__ == "__main__":
#     load_dotenv()
#     today_str = datetime.now().strftime("%Y-%m-%d")
#     super_agent = create_super_agent(today_str=today_str)

#     # 두 전문가의 협업이 필요한 복합 쿼리
#     query = "최신 AI 기술 동향에 대해 TechCrunch에서 검색해서, 그 내용을 바탕으로 우리 팀에게 공유할 메일 초안을 작성해줘. 받는 사람은 'dev_team@mycompany.com' 이야."
#     today_str = datetime.now().strftime("%Y-%m-%d")

#     print(f"\n==================================================")
#     print(f"[사용자 쿼리]: {query}")
#     print(f"==================================================")

#     result = super_agent.invoke(
#         {"input": query, "today": today_str, "chat_history": []}
#     )

#     ai_response = result["output"]
#     print(f"\n[슈퍼 에이전트 최종 답변]: {ai_response}")


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
