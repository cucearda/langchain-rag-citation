# GrobidParser does not extract authors or publication year from TEI header

**Repository:** [langchain-ai/langchain-community](https://github.com/langchain-ai/langchain-community)

## Checked other resources

- [x] This is a bug, not a usage question.
- [x] I added a clear and descriptive title that summarizes this issue.
- [x] I used the GitHub search to find a similar question and didn't find it.
- [x] I am sure that this is a bug in LangChain Community rather than my code.
- [x] The bug is not resolved by updating to the latest stable version of LangChain Community.
- [x] I read what a [minimal reproducible example](https://stackoverflow.com/help/minimal-reproducible-example) is.
- [x] I posted a self-contained, minimal, reproducible example. A maintainer can copy it and run it AS IS.

## Example Code

```python
from langchain_community.document_loaders.parsers import GrobidParser
from langchain_community.document_loaders.generic import GenericLoader

# Requires a running Grobid server:
# docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.1

loader = GenericLoader.from_filesystem(
    ".",
    glob="paper.pdf",  # any academic PDF
    suffixes=[".pdf"],
    parser=GrobidParser(segment_sentences=False),
)

docs = loader.load()
print(docs[0].metadata.keys())
# dict_keys(['text', 'para', 'bboxes', 'pages', 'section_title', 'section_number', 'paper_title', 'file_path'])
#
# 'authors' and 'year' are NOT present
```

## Description

* I'm using `GrobidParser` to parse academic PDFs and extract structured metadata for a citation pipeline.
* I expect each `Document.metadata` to include `authors` and `year` (publication year), since Grobid extracts this information from the PDF.
* Instead, authors and year are silently discarded. Only body-level metadata is returned.

### Root cause

In `lazy_parse()` ([grobid.py line 132](https://github.com/langchain-ai/langchain-community/blob/main/libs/community/langchain_community/document_loaders/parsers/grobid.py)), the parser sends `consolidateHeader=1` to the Grobid API, which instructs Grobid to extract and consolidate header metadata. Grobid responds with a full TEI XML document where `<teiHeader>` contains:

- **Authors:** `<author>/<persName>/<forename>` + `<surname>`
- **Publication date:** `<date type="published" when="YYYY-MM-DD">`

However, `process_xml()` ([line 38](https://github.com/langchain-ai/langchain-community/blob/main/libs/community/langchain_community/document_loaders/parsers/grobid.py)) only parses the `<body>`:

```python
soup = BeautifulSoup(xml_data, "xml")
sections = soup.find_all("div")      # body sections only
titles = soup.find_all("title")       # paper title only
```

It never reads the `<teiHeader>` element, so authors and publication year are requested from Grobid but then thrown away.

### Why this matters

Grobid's primary use case is parsing academic/scientific papers. Authors and publication year are essential metadata for:
- Citation generation (e.g. "Author et al., 2020")
- Bibliography construction
- Document deduplication and identification

These are core reasons someone would choose Grobid over simpler PDF parsers.

### Suggested fix

Add header parsing at the top of `process_xml()`, after the BeautifulSoup initialization:

```python
# Extract header metadata
header = soup.find("teiHeader")
authors = []
year = None
if header:
    for author in header.find_all("author"):
        persname = author.find("persName")
        if persname:
            forename = persname.find("forename")
            surname = persname.find("surname")
            parts = []
            if forename:
                parts.append(forename.text.strip())
            if surname:
                parts.append(surname.text.strip())
            if parts:
                authors.append(" ".join(parts))
    date_tag = header.find("date", {"type": "published"})
    if date_tag and date_tag.get("when"):
        year = date_tag["when"][:4]
```

Then include in the metadata dict yielded for each chunk:

```python
"authors": ", ".join(authors) if authors else None,
"year": year,
```

## System Info

```
langchain-community==0.4.1
langchain-core==1.2.14
Python 3.13
macOS Darwin 24.6.0
```
