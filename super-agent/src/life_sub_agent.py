from function.tour.kr_tour import *
from function.weather.weather_tools import *
from function.shopping.shopping_tools import *
from function.place.naver_place_tools import *
import sys
from langchain.tools import Tool
from openai import OpenAI

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timedelta

load_dotenv()


sys.path.append("/app/ica_project2/function-agent/")


def create_life_sub_agent(eval_mode=False):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
            ### Job Description
            당신은 생활 답변 전문 비서입니다. 사용자의 질문에 따라 장소, 날씨, 쇼핑 관련 함수를 수행하여 결과를 반환합니다.
        """,
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    tools = [
        search_naver_places,
        search_tourist_info,
        get_naver_search_results,
        add_product_to_mycart,
        get_weather
    ]

    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)

    # if eval_mode:
    #     agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)
    # else:
    #     agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    return agent_executor
