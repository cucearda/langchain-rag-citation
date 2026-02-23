from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.tools import tool

from vector_store import get_vector_store
from models import Citation, CitatorResult

vector_store = get_vector_store()

retrieve_documents_for_claim_schema = {
    "type": "object",
    "properties": {
        "claim": {"type": "string"},
        "k": {"type": "number"},
    },
    "required": ["claim", "k"],
}


@tool(
    description="Retrieve top k documents for a given claim from the vector store",
    args_schema=retrieve_documents_for_claim_schema,
    response_format="content_and_artifact",
)
def retrieve_documents_for_claim(claim: str, k: int):
    """Retrieve documents for a given claim."""
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": k, "score_threshold": 0.5},
    )
    response = retriever.invoke(claim)
    for doc in response:
        doc.metadata.pop("bboxes", None)
        doc.metadata["claim"] = claim
    return ("RetrievedDocumentsForClaim", response)


RETRIEVER_SYSTEM_PROMPT = (
    "You are a research assistant. Given a paragraph, dissect the paragraph into claims "
    "and use the retrieve_documents_for_claim tool to find 1 supporting document for EACH claim. "
    "Call the tool once per claim. Return all retrieved documents. "
    "Do not make up any claims, only use the ones that are stated in the paragraph."
)

model = ChatAnthropic(
    model="claude-sonnet-4-20250514", temperature=0, max_tokens=1000, timeout=60
)

document_retriever_agent = create_agent(
    model,
    [retrieve_documents_for_claim],
    system_prompt=RETRIEVER_SYSTEM_PROMPT,
)

CITATOR_SYSTEM_PROMPT = """You are a research assistant. Given a paragraph and a set of source documents, identify every claim in the paragraph that is supported by the provided documents.

For each supported claim:
1. Determine the exact character range (start, end) of the claim text within the paragraph (0-indexed, end is exclusive).
2. State why you chose this source for this claim.
3. Copy a verbatim excerpt from the source document that directly supports the claim.
4. Explain how that excerpt supports the claim.

Only produce citations for claims that are clearly supported by the provided documents. Do not invent citations.

You will return a structured list of Citation objects — one per supported claim.
"""

citator_agent = create_agent(
    model,
    system_prompt=CITATOR_SYSTEM_PROMPT,
    response_format=CitatorResult,
)


def invoke_retriever(paragraph: str):
    """Invoke the retriever agent. Returns a list of retrieved documents."""
    result = document_retriever_agent.invoke(
        {"messages": [{"role": "user", "content": paragraph}]}
    )
    docs = []
    for msg in result["messages"]:
        if hasattr(msg, "artifact") and msg.artifact:
            docs.extend(msg.artifact)
    return docs


def invoke_citator(documents, paragraph) -> list[Citation]:
    """Invoke the citator agent. Returns a list of Citation objects."""
    document_messages = []
    seen_ids = set()
    for doc in documents:
        if doc.id in seen_ids:
            continue
        seen_ids.add(doc.id)
        document_messages.append({
            "role": "system",
            "content": (
                f"Paper title: {doc.metadata['paper_title']}\n"
                f"Section title: {doc.metadata['section_title']},\n"
                f"Pages: {doc.metadata['pages']}\n"
                f"Authors: {doc.metadata['authors']}\n"
                f"Year: {doc.metadata['year']}\n"
                f"document text: {doc.page_content}\n"
            ),
        })

    result = citator_agent.invoke({"messages": [
        *document_messages,
        {"role": "system", "content": CITATOR_SYSTEM_PROMPT},
        {"role": "user", "content": f"Paragraph: {paragraph}"},
    ]})
    return result["structured_response"].citations


def reconstruct_cited_paragraph(paragraph: str, citations: list[Citation]) -> str:
    """Reconstruct the cited paragraph by inserting APA markers at citation end positions.

    Inserts right-to-left so earlier offsets remain valid.
    """
    sorted_citations = sorted(citations, key=lambda c: c.end, reverse=True)
    result = paragraph
    for citation in sorted_citations:
        first_author = citation.source.authors.split(",")[0].strip()
        apa_marker = f" ({first_author}, {citation.source.year})"
        result = result[:citation.end] + apa_marker + result[citation.end:]
    return result