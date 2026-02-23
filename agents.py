from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.tools import tool

from vector_store import get_vector_store

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

CITATOR_SYSTEM_PROMPT = """You are a research assistant. Given a paragraph and a set of source documents, your task is to insert appropriate APA (7th edition) in-text citations into the paragraph.

Carefully analyze the paragraph and the provided documents. Match claims, facts, or ideas in the paragraph with the most relevant supporting document(s). Only cite information that is clearly supported by the provided documents. 

If no documents are provided, or if a claim is not supported by the documents, do NOT invent or suggest citations.

Use APA 7th edition in-text citation style:
- One author: (Author, Year)
- Two authors: (Author & Author, Year)
- Three or more authors: (Author et al., Year)
- Direct quote: (Author, Year, p. X)
- If citing a specific section instead of a page number (e.g., webpage): (Author, Year, Section Name)

Insert citations naturally at the end of the relevant sentence or clause, before the period.

Suggest as many citations as are appropriate and supported by the documents.

Example:

Input paragraph:
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

Output:
Lorem ipsum dolor sit amet, consectetur adipiscing elit (Farmer, 2009). Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat (Tóibín, 2009, p. 52).
"""

citator_agent = create_agent(model, system_prompt=CITATOR_SYSTEM_PROMPT)


def invoke_citator(documents, paragraph):
    """Invoke the citator agent with retrieved documents and a paragraph."""
    document_messages = []
    for doc in documents:
        document_messages.append({
            "role": "system",
            "content": (
                f"Document title: {doc.metadata['paper_title']} "
                f"Section: {doc.metadata['section_title']}, "
                f"document text: {doc.metadata['text']}"
            ),
        })

    return citator_agent.invoke({"messages": [
        *document_messages,
        {"role": "system", "content": CITATOR_SYSTEM_PROMPT},
        {"role": "user", "content": f"Paragraph: {paragraph}"},
    ]})