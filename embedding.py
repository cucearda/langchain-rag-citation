import voyageai
from dotenv import load_dotenv
from typing import List
from models import Chunk, Embedding

def get_voyage_client():
    return voyageai.Client()

def embed_chunks(chunks: List[Chunk], vo=None) -> List[Embedding]:
    embeddingsList: List[Embedding] = []
    inputs: List[str] = []
    for chunk in chunks:
        inputs.append(chunk.text)


    # Get embeddings from Voyage AI
    raw_embeddings = vo.embed(
        texts=inputs, model="voyage-4-lite", input_type="document"
    )

    for i, raw_embedding in enumerate(raw_embeddings):
        embedding = Embedding(
            chunk=chunks[i],
            embedding=raw_embedding.embedding
        )
        embeddingsList.append(embedding)
