import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pdf_processing.extract_pdf import extract_pdf_text
from pdf_processing.extract_metadata import extract_notice_metadata
from pdf_processing.extract_board import extract_board_of_directors
from resolution_extractor.extract_resolutions import extract_resolutions
import json

text = extract_pdf_text("storage/notices/latest.pdf")

print("=== METADATA ===")
meta = extract_notice_metadata(text)
print(json.dumps(meta, indent=2, ensure_ascii=False))

print()
print("=== BOARD ===")
board = extract_board_of_directors(text)
print(f"Directors found: {len(board)}")
for d in board:
    print(f"  {d['s_no']}. {d['name']} | appt={d['date_of_appointment']} | tenure={d['years_as_director']} | indep={d['independent']} | chair={d['chairman']}")

print()
print("=== RESOLUTIONS ===")
res = extract_resolutions(text)
print(f"Resolutions found: {len(res)}")
for r in res:
    print(f"  {r['resolution_number']}. {r['title'][:70]} | mgmt={r['management_recommendation']} | special={r['special_resolution']}")
