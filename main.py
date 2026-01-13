from fastapi import FastAPI, UploadFile, File
from core import tools
from langchain.agents import  AgentExecutor, create_tool_calling_agent #tool_calling_agent
from core.data_loader import load_and_clean_data
from core.agent import create_agent

app = FastAPI()

agent = None

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload et charge les données bancaires"""
    global agent
    
    content = await file.read()
    df = load_and_clean_data(content)  # À adapter pour bytes
    # Stocker le DataFrame pour les tools
    tools.df = df
    # Créer l'agent
    agent = create_agent()
    return {"message": "Données chargées", "transactions": len(df)}
    

@app.post("/ask")
async def ask_agent(question: str):
    """Pose une question à l'agent"""
    if agent is None:
        return {"error": "Aucun fichier chargé"}
    
    response = agent.invoke({"input": question})
    return {"response": response['output']}