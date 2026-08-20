import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from supabase import create_client

load_dotenv(override=True)

SECTION_NAMES = {
    "Overview",
    "Recommendations",
    "Alternative diagnoses",
    "Risk assessment and risk stratification tools",
    "Imaging",
    "Exercise",
    "Orthotics",
    "Manual therapies",
    "Acupuncture",
    "Electrotherapies",
    "Psychological therapy",
    "Pharmacological management of sciatica",
    "Pharmacological management of low back pain",
    "Invasive treatments for low back pain and sciatica",
    "Spinal injections",
    "Radiofrequency denervation",
    "Epidurals",
    "Surgical interventions",
    "Spinal decompression",
    "Disc replacement",
    "Terms used in this guideline",
    "Rationale and impact",
    "Context",
}

NUMBERED_SECTIONS = {
    "1.1": "Assessment of low back pain and sciatica",
    "1.2": "Non-invasive treatments for low back pain and sciatica",
    "1.3": "Invasive treatments for low back pain and sciatica",
}


def chunks(text: str, size: int = 1800, overlap: int = 250):
    clean = " ".join(text.split())
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        yield clean[start:end]
        if end == len(clean):
            break
        start = end - overlap


def section_for_page(text: str, page_number: int) -> str:
    for line in text.splitlines():
        clean = " ".join(line.split()).strip()
        numbered_match = re.match(r"^(\d+\.\d+)(?:\.\d+)?\s+", clean)
        if numbered_match and numbered_match.group(1) in NUMBERED_SECTIONS:
            return NUMBERED_SECTIONS[numbered_match.group(1)]
        if clean in SECTION_NAMES:
            return clean
    return f"Page {page_number}"


def main():
    pdf_path = Path(sys.argv[1] if len(sys.argv) > 1 else "low-back-pain.pdf")
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    client = create_client(url, key)
    rows = []
    chunk_number = 0
    for page_number, page in enumerate(PdfReader(str(pdf_path)).pages, start=1):
        text = page.extract_text() or ""
        section = section_for_page(text, page_number)
        for part in chunks(text):
            chunk_number += 1
            rows.append({
                "title": pdf_path.stem,
                "page_number": page_number,
                "section": section,
                "chunk_number": chunk_number,
                "content": part,
            })
    if rows:
        client.table("guideline_chunks").delete().in_("title", [pdf_path.stem, "Low back pain and sciatica guideline"]).execute()
        try:
            client.table("guideline_chunks").insert(rows).execute()
        except Exception as error:
            if "column" not in str(error).lower():
                raise
            legacy_rows = [
                {"title": row["title"], "page_number": row["page_number"], "content": row["content"]}
                for row in rows
            ]
            client.table("guideline_chunks").insert(legacy_rows).execute()
            print("Indexed with legacy schema; run supabase_schema.sql and re-index for section/chunk metadata.")
    print(f"Indexed {len(rows)} chunks from {pdf_path}")


if __name__ == "__main__":
    main()
