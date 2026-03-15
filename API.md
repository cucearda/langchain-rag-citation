# RAG Citation API — Integration Guide

## Base URL
```
https://<your-railway-domain>.up.railway.app
```

---

## Authentication

All endpoints require a Firebase ID token passed as a Bearer token in the `Authorization` header.

```
Authorization: Bearer <firebase_id_token>
```

To obtain a token, sign in the user via the Firebase client SDK and call `user.getIdToken()`.

---

## Projects

Projects are isolated workspaces. Each project has its own vector store namespace — documents uploaded to one project are only searchable within that project.

---

### Create Project

```
POST /projects
```

**Request body**
```json
{
  "name": "My Research Project"
}
```

**Response** `201 Created`
```json
{
  "id": "my-research-project",
  "name": "My Research Project",
  "namespace": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-14T07:00:00Z"
}
```

---

### List Projects

```
GET /projects
```

**Response** `200 OK`
```json
[
  {
    "id": "my-research-project",
    "name": "My Research Project",
    "namespace": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-03-14T07:00:00Z"
  }
]
```

---

### Delete Project

Deletes the project and all its documents from the vector store.

```
DELETE /projects/{project_id}
```

**Response** `204 No Content`

---

## Documents

---

### Upload Document

Parses a PDF with GROBID and indexes its contents into the project's vector store.

```
POST /projects/{project_id}/documents
Content-Type: multipart/form-data
```

**Form fields**
| Field | Type | Description |
|-------|------|-------------|
| `file` | PDF file | The PDF to upload |

**Response** `201 Created`
```json
{
  "id": "3f21ab6f-1579-4f53-8b8f-0e0a04265ee4",
  "filename": "paper.pdf",
  "chunks_indexed": 42
}
```

---

### List Documents

```
GET /projects/{project_id}/documents
```

**Response** `200 OK`
```json
[
  {
    "id": "3f21ab6f-1579-4f53-8b8f-0e0a04265ee4",
    "filename": "paper.pdf",
    "chunks_indexed": 42,
    "authors": "John Smith, Jane Doe",
    "year": "2023",
    "created_at": "2026-03-14T07:00:00Z"
  }
]
```

---

### Delete Document

Removes the document metadata and all its vectors from the project's vector store.

```
DELETE /projects/{project_id}/documents/{document_id}
```

**Response** `204 No Content`

---

## Citations

---

### Get Citations

Submits a paragraph and returns APA 7th edition in-text citations for each supported claim, along with the fully cited paragraph.

```
POST /projects/{project_id}/citations
Content-Type: application/json
```

**Request body**
```json
{
  "paragraph": "Transformers have become the dominant architecture in NLP. Attention mechanisms allow models to focus on relevant parts of the input."
}
```

**Response** `200 OK`
```json
{
  "cited_paragraph": "Transformers have become the dominant architecture in NLP (Vaswani et al., 2017, p. 5). Attention mechanisms allow models to focus on relevant parts of the input (Bahdanau et al., 2015, p. 3).",
  "citations": [
    {
      "start": 0,
      "end": 57,
      "citation_format": "(Vaswani et al., 2017, p. 5)",
      "reason": "The claim about transformers dominating NLP is supported by this paper.",
      "relevant_quote": "The Transformer follows an encoder-decoder structure...",
      "relevance_explanation": "This quote introduces the Transformer architecture that became the dominant model.",
      "source": {
        "paper_title": "Attention Is All You Need",
        "authors": "Ashish Vaswani, Noam Shazeer",
        "year": "2017",
        "section_title": "Introduction",
        "section_number": "1",
        "pages": "5"
      }
    }
  ]
}
```

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `cited_paragraph` | string | The original paragraph with APA in-text citations inserted |
| `citations` | array | One entry per supported claim |
| `citations[].start` | integer | Character offset (0-indexed) where the cited claim begins |
| `citations[].end` | integer | Character offset (0-indexed, exclusive) where the cited claim ends |
| `citations[].citation_format` | string | APA 7th edition in-text citation, e.g. `(Smith, 2021, p. 170)` |
| `citations[].reason` | string | Why this source was chosen for this claim |
| `citations[].relevant_quote` | string | Verbatim excerpt from the source that supports the claim |
| `citations[].relevance_explanation` | string | How the quote supports the claim |
| `citations[].source.paper_title` | string | Title of the cited paper |
| `citations[].source.authors` | string | Comma-separated author names |
| `citations[].source.year` | string | Publication year |
| `citations[].source.section_title` | string | Section where the cited text appears |
| `citations[].source.section_number` | string \| null | Section number if available |
| `citations[].source.pages` | string \| null | Page numbers if available |

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `401` | Missing or invalid Firebase token |
| `404` | Project or document not found |
| `500` | Agent failure (retriever or citator) |

All error responses follow the format:
```json
{
  "detail": "Error message here"
}
```
