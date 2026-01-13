from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.agents import  AgentExecutor, create_tool_calling_agent #tool_calling_agent
import core.prompts as prompts
from .tools import analyze_transactions, detect_spending_patterns

from dotenv import load_dotenv

load_dotenv()


def create_agent():
    """Crée et retourne l'agent configuré"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [analyze_transactions, detect_spending_patterns]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompts.PROMPT_BEST), 
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor