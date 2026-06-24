import re
import pdfplumber


def extract_pdf_text(pdf_path):
    """
    Extract and normalize text from a PDF.
    Primary: pypdf (better for multi-column notice PDFs, reads in natural order).
    Fallback: pdfplumber (better for table-heavy InGovern report PDFs).
    Table extraction always uses pdfplumber separately via extract_pdf_tables().
    """
    text = _extract_with_pypdf(pdf_path)
    if not text.strip():
        text = _extract_with_pdfplumber(pdf_path)
    return _normalize(text)


def _extract_with_pypdf(pdf_path, max_pages=None):
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        pages_to_read = reader.pages if max_pages is None else reader.pages[:max_pages]
        pages = []
        for page in pages_to_read:
            extracted = page.extract_text()
            if extracted:
                pages.append(extracted)
        return "\n".join(pages)
    except Exception:
        return ""


def _extract_with_pdfplumber(pdf_path):
    try:
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text(x_tolerance=3, y_tolerance=3)
                if extracted:
                    pages.append(extracted)
        return "\n".join(pages)
    except Exception:
        return ""


def extract_pdf_tables(pdf_path, max_pages=20):
    """
    Extract tables from the PDF using pdfplumber (handles checkmarks, structured tables).
    Only scans the first max_pages pages — board tables appear near the front.
    Returns list of {page, table_index, headers, rows, raw}.
    """
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_scan = pdf.pages[:max_pages]
            for page_num, page in enumerate(pages_to_scan, 1):
                try:
                    tables = page.extract_tables()
                except Exception:
                    continue
                for t_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue
                    cleaned = []
                    for row in table:
                        cleaned.append([_clean_cell(c) for c in row])
                    headers = cleaned[0] if cleaned else []
                    rows = cleaned[1:] if len(cleaned) > 1 else []
                    results.append({
                        "page":        page_num,
                        "table_index": t_idx,
                        "headers":     headers,
                        "rows":        rows,
                        "raw":         cleaned,
                    })
    except Exception:
        pass
    return results


def _clean_cell(cell):
    if cell is None:
        return ""
    s = str(cell).strip().replace("\n", " ")
    return re.sub(r"[ ]{2,}", " ", s).strip()


def _normalize(text):
    text = text.replace("\xa0", " ")
    text = text.replace("\t", " ")
    text = text.replace("\xad", "")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("'", "'")
    text = text.replace("'", "'")
    text = text.replace(""", '"')
    text = text.replace(""", '"')
    text = text.replace("‐", "-")
    text = text.replace("−", "-")
    lines = text.split("\n")
    lines = [re.sub(r"[ ]{2,}", " ", ln) for ln in lines]
    return "\n".join(lines)
