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

import sys

sys.path.append("../function-agent/")
from function.place.naver_place_tools import *
from function.shopping.shopping_tools import *


def create_life_sub_agent():
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
        get_naver_search_results,
        add_product_to_mycart,
    ]

    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    return agent_executor
