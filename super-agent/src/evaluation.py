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
        description=""" 
            해당 도구는 업무를 보조하는 agent 입니다. 
            1. 메일을 검색하거나 메일 초록을 작성하거나, 메일 내용을 요약이 필요할때 활용할 수 있습니다.
            2. 캘린더 일정을 확인하거나 생성, 수정, 삭제하는 등이 필요할때 활용할 수 있습니다.""",
    ),
    Tool(
        name="search_assistant",
        func=lambda user_input: search_agent.invoke(
            {
                "input": user_input,
            }
        ),
        description="""
            해당 도구는 사용자의 요청에 맞는 정보를 검색하는 agent 입니다.
            1. 일반적인 웹 검색이 가능하고.
            2. 특정 도메인에 대한 전문 검색도 가능합니다.
            3. 필요한 정보를 직접 찾아볼 수 있게 링크만 정리해줄 수 도 있습니다.
            """,
    ),
    Tool(
        name="life_assistant",
        func=lambda user_input: life_agent.invoke(
            {
                "input": user_input,
            }
        ),
        description="""
            해당 도구는 생활 편의성을 돕는 어시스턴트입니다.
            1. 사용자가 장소를 검색하고자 할 때 사용할 수 있습니다.
            2. 특정 장소에 대한 날씨 검색 혹은 장소 추천 시 날씨 검색을 할 때 사용할 수 있습니다.
            3. 쇼핑 상품을 검색하거나 장바구니에 저장하고자 할 때 사용할 수 있습니다.
            """,
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
                    - business_assitant : 해당 도구는 업무를 보조하는 agent 입니다. 
                    - search_assistant : 해당 도구는 사용자의 요청에 맞는 정보를 검색하는 agent 입니다.
                    - life_assistant : 해당 도구는 생활 편의성을 돕는 어시스턴트입니다.

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
    today_str += f" AM 10:30"
    super_agent = create_super_agent(today_str = today_str)
    total_result = {}
    for eval_data in EVALUATION_SET:
        eval_data = EVALUATION_SET[9]
        query = eval_data['query']
        total_step = len(eval_data['expected_tool_calls'])

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
        total_result[query] = {"accuracy" : f'{acc_depth_1, total_step}, {acc_depth_2, total_step}',
                               "logs" : result["intermediate_steps"]}
        break
    print(total_result)