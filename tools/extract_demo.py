"""Reproduce factual CSV excerpts from the publisher's downloaded Excel.

No values are generated or adjusted. Keep raw workbooks in data/raw locally.
"""

from pathlib import Path
import csv
import hashlib
import json

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = "https://www.nature.com/articles/s41586-023-06783-1"
BASE = "https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-023-06783-1/MediaObjects/"


def main():
    path = ROOT / "data/raw/chit1_source_data_fig2.xlsx"
    extra_path = ROOT / "data/raw/chit1_source_data_extended_fig3.xlsx"
    sources = {"Fig.2": path, "Extended Data Fig.3": extra_path}
    records = []
    for source_name, source_path in sources.items():
        book = load_workbook(source_path, read_only=True, data_only=True)
        try:
            selected = (
                (("Fig.2b-1", "chit1_fig2b_1.csv", ["P2RY12_negative_percent", "P2RY12_positive_percent"]),
                 ("Fig.2b-2", "chit1_fig2b_2.csv", ["Young", "Aged"])) if source_name == "Fig.2" else
                (("Extended Data Fig.3f-1", "chit1_ext3f_1.csv", ["MS4A7_negative_percent", "MS4A7_positive_percent"]),
                 ("Extended Data Fig.3f-3", "chit1_ext3f_3.csv", ["Young", "Aged"]),
                 ("Extended Data Fig.3c-2", "chit1_ext3c_2.csv", ["Young", "Aged"]),
                 ("Extended Data Fig.3f-2", "chit1_ext3f_2.csv", ["Young", "Aged"]))
            )
            for sheet, filename, headers in selected:
                rows = list(book[sheet].values)
                measured = [list(row[:2]) for row in rows[2:]]
                while measured and all(value is None for value in measured[-1]):
                    measured.pop()
                _save_csv(filename, headers, measured)
                records.append({
                    "file": filename, "dataset_name": sheet, "source_sheet": sheet,
                    "source_file": "raw/" + source_path.name,
                    "source_excel_range": f"A3:B{len(measured) + 2}",
                    "column_labels": headers, "shape": [len(measured), 2],
                    "description": str(rows[0][0]),
                    "sha256": hashlib.sha256((ROOT / "data" / filename).read_bytes()).hexdigest(),
                })
        finally:
            book.close()
    provenance = {
        "article_title": "CHIT1-positive microglia drive motor neuron ageing in the primate spinal cord",
        "article_url": ARTICLE, "doi": "10.1038/s41586-023-06783-1",
        "downloaded_at": "2026-09-27",
        "author_correction": "https://doi.org/10.1038/s41586-026-10728-9",
        "source_url": BASE + "41586_2023_6783_MOESM5_ESM.xlsx",
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "extended_fig3_source": {
            "file": "raw/" + extra_path.name,
            "url": BASE + "41586_2023_6783_MOESM11_ESM.xlsx",
            "sha256": hashlib.sha256(extra_path.read_bytes()).hexdigest(),
        },
        "additional_source": {
            "file": "raw/chit1_source_data_extended_fig5.xlsx",
            "url": BASE + "41586_2023_6783_MOESM12_ESM.xlsx",
            "sha256": hashlib.sha256((ROOT / "data/raw/chit1_source_data_extended_fig5.xlsx").read_bytes()).hexdigest(),
        },
        "extraction": "Exact numeric values from the stated cell ranges; headers renamed. Statistical annotation columns omitted. No values fabricated or corrected.",
        "interpretation": "Publicly discussed dataset used to demonstrate numerical screening, not a misconduct verdict. Download reflects current publisher files, not a reconstructed original version.",
        "rights": "Article is under exclusive licence to Springer Nature. Raw publisher workbooks are local-only, excluded from Git/package. Bundled CSVs contain a small factual numerical excerpt with attribution; no article text/images are reproduced.",
        "datasets": records,
    }
    for folder in (ROOT / "data", ROOT / "src/sci_fakedata/datasets"):
        (folder / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Extracted unmodified numeric blocks and recorded SHA-256 provenance.")


def _save_csv(filename, headers, measured):
    for folder in (ROOT / "data", ROOT / "src/sci_fakedata/datasets"):
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerows(measured)


if __name__ == "__main__":
    main()
