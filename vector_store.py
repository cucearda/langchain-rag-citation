import os

from dotenv import load_dotenv
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


def get_vector_store():
    pc = get_pinecone_client()

    if not pc.has_index(INDEX_NAME):
        pc.create_index(
            name=INDEX_NAME,
            dimension=1024,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    index = pc.Index(INDEX_NAME)
    embeddings = get_embeddings()

    return PineconeVectorStore(index=index, embedding=embeddings)
