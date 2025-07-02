from langchain.tools import Tool
from openai import OpenAI

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import  AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timedelta
load_dotenv()

import sys
sys.path.append('../function-agent/') # 각 환경에 맞게 python path를 수정해야합니다 .
from function.mail_agent.src.main import *





def create_business_sub_agent():
    now = datetime.now().strftime('%Y-%m-%d')

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
            ### Job Description
            당신은 비즈니스 전문 AI Assistant로, 사용자의 비즈니스 메일 등을 관리합니다.
            사용자의 요청에 맞는 function을 선택하여 수행 후 해당 결과를 상대에게 반환해주면 됩니다
            확실하지 않은 정보는 Basic Info 를 확인하여 답하면 됩니다

            ### Basic Info
            - 오늘 날짜: {now}
            - 
        """),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    tools = [find_mails, draft_mail, summarize_conversation_in_mails]
    
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    
    return agent_executor