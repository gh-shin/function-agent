import logging
from flask import Flask, request, jsonify, Response
from datetime import datetime
from dotenv import load_dotenv
import os
import json

# CORS setup
from flask_cors import CORS

# LangChain and OpenAI imports
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import sub-agents
# Make sure these files exist in your project directory
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from business_sub_agent import create_business_sub_agent
from life_sub_agent import create_life_sub_agent
from search_sub_agent import create_search_sub_agent

# Import the new stock analysis function
from stock.stock_sub_agent import run_stock_analysis

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app and CORS
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# --- Create Sub-Agent Instances ---
# Note: These are assumed to be defined in their respective files
business_agent = create_business_sub_agent()
life_agent = create_life_sub_agent()
search_agent = create_search_sub_agent()

# --- Define Tools for the Orchestrator ---
# This list now includes the new stock_assistant
orchestrator_tools = [
    Tool(
        name="business_assistant",
        func=lambda user_input: business_agent.invoke({"input": user_input}),
        description="비즈니스, 경제, 재무 관련 질문에 답변하는 전문가.",
    ),
    Tool(
        name="search_assistant",
        func=lambda user_input: search_agent.invoke({"input": user_input}),
        description="웹 검색이 필요한 최신 정보나 특정 주제에 대한 검색을 수행하는 전문가.",
    ),
    Tool(
        name="life_assistant",
        func=lambda user_input: life_agent.invoke({"input": user_input}),
        description="일상 생활, 여행, 취미 등 일반적인 주제에 대해 답변하는 전문가.",
    ),
    Tool(
        name="stock_assistant",
        func=run_stock_analysis, # Use the new function directly
        description="삼성전자, SK하이닉스 등 특정 주식의 가격, 거래량, 추세에 대한 질문에 답변하는 주식 전문가.",
    ),
]

# --- Create the Super Agent (Orchestrator) ---
def create_super_agent():
    """Creates the main agent executor that orchestrates sub-agents."""
    now = datetime.now().strftime("%Y-%m-%d")
    # Updated prompt to include the new stock_assistant
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""You are a master AI assistant (super agent). Your role is to analyze the user's complex requests and accurately delegate the task to the appropriate specialist assistant.
                
                Here is the list of available specialists:
                - business_assistant: Specialist for business, economy, and finance-related questions.
                - search_assistant: Specialist for performing web searches for the latest information.
                - life_assistant: Specialist for general topics like daily life, travel, and hobbies.
                - stock_assistant: Specialist for answering questions about specific stock prices, volume, and trends.

                Today's date is {now}.
                You must select the most appropriate specialist for the user's query.
                """,
            ),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
    agent = create_openai_functions_agent(llm, orchestrator_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=orchestrator_tools, verbose=True)

    return agent_executor

# Create a single instance of the super_agent
super_agent = create_super_agent()

# --- Flask API Endpoints ---
@app.route("/api/ping", methods=["GET"])
def health_check():
    """A simple endpoint to check if the server is running."""
    logging.info("Health check endpoint was called.")
    return jsonify({
        "status": "ok",
        "message": "🎯 Server is up and running.",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route("/api/superagent", methods=["POST"])
def superagent_api():
    """The main endpoint to interact with the super agent."""
    data = request.json
    user_query = data.get("query")

    if not user_query:
        logging.warning("Request received without a 'query' field.")
        return Response(
            json.dumps({"error": "The 'query' field is required."}, ensure_ascii=False),
            status=400,
            content_type="application/json"
        )

    logging.info(f"Received query for superagent: '{user_query}'")
    try:
        # Invoke the super agent with the user's query
        result = super_agent.invoke({
            "input": user_query,
            "chat_history": [] # Managing chat history can be implemented here
        })
        
        # The final answer is in the 'output' key
        answer = result.get("output", "Sorry, I couldn't process your request.")
        
        return Response(
            json.dumps({"answer": answer}, ensure_ascii=False),
            status=200,
            content_type="application/json"
        )
    except Exception as e:
        logging.error(f"An error occurred in superagent_api: {e}", exc_info=True)
        return Response(
            json.dumps({"error": f"An internal server error occurred: {str(e)}"}, ensure_ascii=False),
            status=500,
            content_type="application/json"
        )

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting Flask server...")
    # Use debug=False in a production environment
    app.run(host="0.0.0.0", port=8000, debug=True)
