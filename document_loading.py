from grobid_client.grobid_client import GrobidClient
import xml.etree.ElementTree as ET

GROBID_URL = "http://localhost:8070"
TEI_NS = "{http://www.tei-c.org/ns/1.0}"

def parse_pdf_with_grobid(file_path: str) -> dict:
    """Parse an academic PDF into structured sections using GROBID."""
    client = GrobidClient(grobid_server=GROBID_URL)
    _, _, xml_content = client.process_pdf(
        "processFulltextDocument",
        file_path,
        generateIDs=True,
        consolidate_citations=True,
    )

    root = ET.fromstring(xml_content)
    sections = {}

    # Extract title
    title_el = root.find(f".//{TEI_NS}titleStmt/{TEI_NS}title")
    if title_el is not None and title_el.text:
        sections["title"] = title_el.text.strip()

    # Extract abstract
    abstract_el = root.find(f".//{TEI_NS}profileDesc/{TEI_NS}abstract")
    if abstract_el is not None:
        sections["abstract"] = " ".join(abstract_el.itertext()).strip()

    # Extract body sections
    body = root.find(f".//{TEI_NS}body")
    if body is not None:
        for div in body.findall(f"{TEI_NS}div"):
            head = div.find(f"{TEI_NS}head")
            heading = head.text.strip() if head is not None and head.text else "Untitled Section"
            paragraphs = [
                " ".join(p.itertext()).strip()
                for p in div.findall(f"{TEI_NS}p")
            ]
            sections[heading] = "\n\n".join(paragraphs)

    # Extract references
    bibl_list = root.findall(f".//{TEI_NS}listBibl/{TEI_NS}biblStruct")
    references = []
    for bibl in bibl_list:
        ref_title = bibl.find(f".//{TEI_NS}title")
        if ref_title is not None and ref_title.text:
            references.append(ref_title.text.strip())
    if references:
        sections["references"] = references

    return sections


if __name__ == "__main__":
    result = parse_pdf_with_grobid("hope.pdf")
    for section, content in result.items():
        if isinstance(content, list):
            print(f"\n=== {section} ({len(content)} items) ===")
            for item in content[:3]:
                print(f"  - {item}")
        else:
            print(f"\n=== {section} ===")
            print(content[:200] + "..." if len(content) > 200 else content)
