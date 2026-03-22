import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from langchain_pinecone import PineconeVectorStore
from langchain_voyageai import VoyageAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

INDEX_NAME = "langchain-test-index"


def get_pinecone_client():
    return Pinecone()


def get_embeddings():
    return VoyageAIEmbeddings(
        voyage_api_key=os.getenv("VOYAGE_API_KEY"), model="voyage-4-lite"
    )

def initialize_vector_store_index():
    pc = get_pinecone_client()

    if not pc.has_index(INDEX_NAME):
        pc.create_index(
            name=INDEX_NAME,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc.Index(INDEX_NAME)

def get_vector_store_by_namespace(embeddings: VoyageAIEmbeddings, index: Pinecone, namespace: str = ""):
    try:
        return PineconeVectorStore(index=index, embedding=embeddings, namespace=namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing vector store: {e}")

def get_retriever(vector_store: PineconeVectorStore):
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 3, "score_threshold": 0.5}
    )


def delete_document_chunks(index, doc_id: str) -> int:
    result = index.query(
        vector=[0.0] * 1024,
        top_k=10000,
        filter={"doc_id": {"$eq": doc_id}},
        include_metadata=False,
    )
    ids = [m["id"] for m in result["matches"]]
    if ids:
        index.delete(ids=ids)
    return len(ids)


def list_document_chunks(index, doc_id: str) -> list[dict]:
    result = index.query(
        vector=[0.0] * 1024,
        top_k=10000,
        filter={"doc_id": {"$eq": doc_id}},
        include_metadata=True,
    )
    return result.get("matches", [])