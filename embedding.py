import voyageai
from dotenv import load_dotenv
from typing import List

load_dotenv()

def get_voyage_client():
    return voyageai.Client()

def embed_chunks(chunks: List[Chunk], vo=None) -> List[EmbeddedChunk]:
    """
    Embed chunks using Voyage AI and return EmbeddedChunk objects.
    
    Args:
        chunks: List of Chunk objects to embed
        
    Returns:
        List of EmbeddedChunk objects with embeddings
    """
    if not chunks:
        return []
        
    embedded_chunks: List[EmbeddedChunk] = []
    inputs: List[str] = []
    for chunk in chunks:
        inputs.append(chunk.text)

    # Get embeddings from Voyage AI
    embds_obj = vo.embed(
        texts=inputs, model="voyage-4-lite", input_type="document"
    )
    
    # Extract embeddings from the response
    embeddings = embds_obj.embeddings
    
    # Create EmbeddedChunk objects
    for i, chunk in enumerate(chunks):
        # Generate a unique vector ID for Pinecone
        vector_id = f"chunk_{chunk.chunk_id}"
        
        embedded_chunk = EmbeddedChunk(
            chunk=chunk,
            vector_id=vector_id,
            embedding=embeddings[i]
        )
        embedded_chunks.append(embedded_chunk)
    
    return embedded_chunks