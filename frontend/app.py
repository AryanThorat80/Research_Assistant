import streamlit as st
import requests

# FastAPI backend URL
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Multi-Agent Research Assistant", page_icon="🤖", layout="wide")

st.title("🤖 Multi-Agent AI Research Assistant")
st.markdown("Powered by **LangGraph, Mistral AI, ChromaDB, and Tavily Search**")

# Sidebar for Document Ingestion
with st.sidebar:
    st.header("📂 Document Ingestion (RAG)")
    st.markdown("Upload research notes or text to query locally.")
    
    doc_text = st.text_area("Paste document content here:")
    doc_source_name = st.text_input("Source Name (e.g., notes.txt)", value="user_note.txt")
    
    if st.button("Ingest Document"):
        if doc_text.strip():
            with st.spinner("Ingesting into ChromaDB..."):
                try:
                    payload = {
                        "texts": [doc_text],
                        "metadatas": [{"source": doc_source_name}]
                    }
                    response = requests.post(f"{BACKEND_URL}/ingest", json=payload)
                    if response.status_code == 200:
                        st.success(f"Successfully ingested {response.json().get('chunks_ingested', 0)} chunks!")
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")
        else:
            st.warning("Please enter some text to ingest.")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "plan" in message and message["plan"]:
            with st.expander("🔍 View Research Plan"):
                st.markdown(message["plan"])
        if "sources" in message and message["sources"]:
            with st.expander("📚 Sources & References"):
                for src in message["sources"]:
                    st.markdown(f"- {src}")

# User input handling
if user_query := st.chat_input("Ask a research question..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Call FastAPI backend
    with st.chat_message("assistant"):
        with st.spinner("Agents are planning, searching the web, and analyzing documents..."):
            try:
                payload = {"message": user_query}
                response = requests.post(f"{BACKEND_URL}/chat", json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("response", "No response.")
                    plan = data.get("plan", "")
                    docs = data.get("documents_used", [])
                    web_res = data.get("web_results_used", [])
                    
                    st.markdown(answer)
                    
                    if plan:
                        with st.expander("🔍 View Research Plan"):
                            st.markdown(plan)
                            
                    sources = docs + web_res
                    if sources:
                        with st.expander("📚 Sources & References"):
                            for src in sources:
                                st.markdown(f"- {src[:200]}...")
                                
                    # Save assistant response to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "plan": plan,
                        "sources": sources
                    })
                else:
                    st.error(f"Backend error: {response.text}")
            except Exception as e:
                st.error(f"Could not reach FastAPI backend. Make sure it's running! Error: {e}")