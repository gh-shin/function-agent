from langchain.tools import Tool
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

import sys

sys.path.append("/app/ica_project2/function-agent/")
from business_sub_agent import create_business_sub_agent
from life_sub_agent import create_life_sub_agent
from search_sub_agent import create_search_sub_agent

# 각 분야별 sub agent
business_agent = create_business_sub_agent(eval_mode=True)
life_agent = create_life_sub_agent(eval_mode=True)
search_agent = create_search_sub_agent(eval_mode=True)


# orchestrator tools
orchestrator_tools = [
    Tool(
        name="business_assitant",
        func=lambda user_input: business_agent.invoke(
            {
                "input": user_input,
            }
        ),
        description="""프롬프트트""",
    ),
    Tool(
        name="search_assistant",
        func=lambda user_input: search_agent.invoke(
            {
                "input": user_input,
            }
        ),
        description="""프롬프트ㅜㅠㅠㅜ.""",
    ),
    Tool(
        name="life_assistant",
        func=lambda user_input: life_agent.invoke(
            {
                "input": user_input,
            }
        ),
        description="""프롬프트ㅜㅠㅠㅜ.""",
    ),
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
    agent_executor = AgentExecutor(agent=agent, tools=orchestrator_tools, verbose=True, return_intermediate_steps=True)

    return agent_executor


if __name__ == "__main__":
    from evaluation_data import EVALUATION_SET


    load_dotenv()
    today_str = datetime.now().strftime("%Y-%m-%d")
    super_agent = create_super_agent(today_str = today_str)
    total_result = {}
    for eval_data in EVALUATION_SET:
        # eval_data = EVALUATION_SET[5]
        query = eval_data['query']
        total_step = len(eval_data['expected_tool_calls'])
        
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
        print(result['intermediate_steps'])
        acc_depth_1 = 0
        acc_depth_2 = 0
        for i in range(total_step):
            try:
                each_step = eval_data['expected_tool_calls'][i]
                if each_step['agent_name'] == result['intermediate_steps'][i][0].tool:
                    acc_depth_1 += 1
                if each_step['function_name'] == result['intermediate_steps'][i][1]['intermediate_steps'][0][0].tool:
                    acc_depth_2 += 1
            except:
                pass

        print(f"[사용자 쿼리]: {query}")
        print(f'accuracy : {acc_depth_1, total_step}, {acc_depth_2, total_step}')
        total_result[query] = f'accuracy : {acc_depth_1, total_step}, {acc_depth_2, total_step}'
    
    print(total_result)