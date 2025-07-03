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
from function.search_agent.src.main import (
    tavily_qa_tool,
    tech_search_tool,
    find_links_tool,
)


def create_search_sub_agent():
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""
            ### Job Description
            사용자에게 답변 시 정보가 부족할 경우 검색하여 답변을 해주는 검색 전문 비서입니다.
            만약, 사용자가 특정 검색을 원할 경우에도 해당 비서는 작동합니다.
        """,
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    tools = [
        tavily_qa_tool,
        tech_search_tool,
        find_links_tool,
    ]

    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    return agent_executor
