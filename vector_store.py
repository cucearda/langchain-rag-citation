from pinecone import Pinecone
from dotenv import load_dotenv
from typing import List
from models import Embedding

load_dotenv()

def get_pinecone_client():
    return Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def upsert_embeddings(embeddings: List[Embedding]):
    pinecone.upsert(
        embeddings=embeddings,
        namespace="test"
    )