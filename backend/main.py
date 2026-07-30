from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage
from backend.agents import research_graph
from backend.rag import ingest_documents
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Multi-Agent Research Assistant API", version="1.0")

class QueryRequest(BaseModel):
    message: str
    collection_name: Optional[str] = "research_docs"

class QueryResponse(BaseModel):
    response: str
    plan: Optional[str] = None
    documents_used: List[str] = []
    web_results_used: List[str] = []

class IngestRequest(BaseModel):
    texts: List[str]
    metadatas: Optional[List[dict]] = None
    collection_name: Optional[str] = "research_docs"

@app.post("/chat", response_model=QueryResponse)
def chat_endpoint(request: QueryRequest):
    """Runs the LangGraph multi-agent workflow for a given user query."""
    try:
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "documents": [],
            "web_results": [],
            "plan": "",
            "final_report": ""
        }
        
        # Invoke LangGraph workflow
        result = research_graph.invoke(initial_state)
        
        return QueryResponse(
            response=result.get("final_report", "No response generated."),
            plan=result.get("plan", ""),
            documents_used=result.get("documents", []),
            web_results_used=result.get("web_results", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
def ingest_endpoint(request: IngestRequest):
    """Ingests raw text documents into ChromaDB for RAG."""
    try:
        count = ingest_documents(
            texts=request.texts, 
            metadatas=request.metadatas, 
            collection_name=request.collection_name
        )
        return {"status": "success", "chunks_ingested": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Multi-Agent Research Assistant API is running!"}