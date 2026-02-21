from langchain_community.document_loaders.parsers import GrobidParser
from langchain_community.document_loaders.generic import GenericLoader
from langchain_text_splitters import CharacterTextSplitter
from models import Chunk

def parse_pdf_with_grobid(file_path: str) -> dict:
   # Load
    loader = GenericLoader.from_filesystem(
        ".",
        glob="hope.pdf",
        suffixes=[".pdf"],
        parser=GrobidParser(segment_sentences=False)
    )
    docs = {}
    try :
        docs = loader.load()
    except Exception as e:
            print(f"Error: {e}")
    return docs

def split_chunks(docs: dict) -> list:
    chunks: list[Chunk] = []
    for doc in docs:
        text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base", chunk_size=1500, chunk_overlap=300
        )
        texts = text_splitter.split_text(doc.page_content)
        for i, text in enumerate(texts):
            chunk = Chunk(
                text=text,
                paragraph=doc.metadata["para"],
                pages=doc.metadata["pages"],
                section_title=doc.metadata["section_title"],
                section_number=doc.metadata["section_number"],
                paper_title=doc.metadata["paper_title"],
            )
            chunks.append(chunk)
    return chunks