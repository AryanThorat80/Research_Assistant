import os
from typing import TypedDict, List, Annotated
import operator
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
from backend.rag import search_documents

# Initialize Mistral LLM and Tavily Client
llm = ChatMistralAI(model="mistral-large-latest", temperature=0.2)
tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

# Define Agent State
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage], operator.add]
    documents: List[str]
    web_results: List[str]
    plan: str
    final_report: str

def planner_node(state: AgentState):
    """Decides the execution path and strategy based on the latest user query."""
    messages = state["messages"]
    latest_query = messages[-1].content
    
    prompt = f"""You are a research planner coordinator. 
    Analyze the user query: '{latest_query}'
    Determine if we need to search local documents, perform a web search, or both.
    Provide a brief plan."""
    
    response = llm.invoke([SystemMessage(content=prompt)] + messages)
    return {"plan": response.content}

def rag_node(state: AgentState):
    """Retrieves context from local vector database (ChromaDB)."""
    messages = state["messages"]
    query = messages[-1].content
    
    docs = search_documents(query, k=3)
    doc_texts = [d.page_content for d in docs]
    
    return {"documents": doc_texts}

def web_search_node(state: AgentState):
    """Performs live web search using Tavily."""
    messages = state["messages"]
    query = messages[-1].content
    
    try:
        search_response = tavily.search(query=query, max_results=3)
        results = [r["content"] for r in search_response.get("results", [])]
    except Exception as e:
        results = [f"Web search failed: {str(e)}"]
        
    return {"web_results": results}

def writer_node(state: AgentState):
    """Synthesizes documents, web results, and chat history into a final citation-backed response."""
    messages = state["messages"]
    docs = state.get("documents", [])
    web_results = state.get("web_results", [])
    
    context = "\n\n".join([f"[Local Doc]: {d}" for d in docs] + [f"[Web Result]: {w}" for w in web_results])
    
    system_prompt = f"""You are an advanced Multi-Agent AI Research Assistant. 
    Synthesize the information from the provided context (local uploaded documents and web search results) to answer the user query comprehensively. 
    Always provide clear source citations/references based on the context.

    Context:
    {context}
    """
    
    response = llm.invoke([SystemMessage(content=system_prompt)] + messages)
    return {"final_report": response.content, "messages": [AIMessage(content=response.content)]}

# Build LangGraph Workflow
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("rag_retriever", rag_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("writer", writer_node)

# Set up edges
workflow.set_entry_point("planner")
workflow.add_edge("planner", "rag_retriever")
workflow.add_edge("planner", "web_search")
workflow.add_edge("rag_retriever", "writer")
workflow.add_edge("web_search", "writer")
workflow.add_edge("writer", END)

research_graph = workflow.compile()