from typing import List
from chromadb import PersistentClient
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_mistralai import MistralAIEmbeddings

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

# Initialize ChromaDB persistent client
CHROMA_PATH = "chroma_db"
db_client = PersistentClient(path=CHROMA_PATH)

# Initialize Mistral Embeddings
# Note: Ensure MISTRAL_API_KEY is set in your .env file
embeddings = MistralAIEmbeddings(model="mistral-embed")

def get_or_create_collection(collection_name: str = "research_docs"):
    """Gets or creates a ChromaDB collection."""
    return db_client.get_or_create_collection(name=collection_name)

def ingest_documents(texts: List[str], metadatas: List[dict] = None, collection_name: str = "research_docs"):
    """Splits text documents and stores them into ChromaDB with embeddings."""
    collection = get_or_create_collection(collection_name)
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    
    docs = []
    for i, text in enumerate(texts):
        meta = metadatas[i] if metadatas and i < len(metadatas) else {"source": f"doc_{i}"}
        chunks = splitter.split_text(text)
        for chunk in chunks:
            docs.append(Document(page_content=chunk, metadata=meta))
            
    if not docs:
        return 0

    # Generate embeddings and add to Chroma collection
    texts_to_add = [doc.page_content for doc in docs]
    metadatas_to_add = [doc.metadata for doc in docs]
    ids = [f"doc_{i}_{idx}" for idx in range(len(docs))]
    
    vector_embeddings = embeddings.embed_documents(texts_to_add)
    
    collection.add(
        ids=ids,
        embeddings=vector_embeddings,
        documents=texts_to_add,
        metadatas=metadatas_to_add
    )
    return len(docs)

def search_documents(query: str, k: int = 4, collection_name: str = "research_docs") -> List[Document]:
    """Performs semantic similarity search against ChromaDB."""
    collection = get_or_create_collection(collection_name)
    query_embedding = embeddings.embed_query(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )
    
    documents = []
    if results and "documents" in results and results["documents"]:
        for doc_text, meta in zip(results["documents"][0], results["metadatas"][0]):
            documents.append(Document(page_content=doc_text, metadata=meta))
            
    return documents