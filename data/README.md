# Demo data provenance

The public-data demo uses numeric excerpts from Sun, S., Li, J., Wang, S. et al., **CHIT1-positive microglia drive motor neuron ageing in the primate spinal cord**. *Nature* 624, 611–620 (2023). [Article / Source Data downloads](https://www.nature.com/articles/s41586-023-06783-1).

The corresponding author list includes Jing Qu (曲静). This paper was selected from the publicly discussed case; a numerical pattern does not establish misconduct. The [2 June 2026 author correction](https://doi.org/10.1038/s41586-026-10728-9) concerns Extended Data Fig. 9d. Downloads reflect the current publisher snapshot, not an archived reconstruction of the original files.

| File | Publisher worksheet | Extracted cells |
| --- | --- | --- |
| `chit1_fig2b_1.csv` | `Fig.2b-1` | `A3:B18`, 16 observations, negative/positive P2RY12 percentages |
| `chit1_fig2b_2.csv` | `Fig.2b-2` | `A3:B10`, 8 observations, Young/Aged measurements |
| `chit1_ext3f_1.csv` | `Extended Data Fig.3f-1` | `A3:B18`, 16 observations, negative/positive MS4A7 percentages |
| `chit1_ext3f_3.csv` | `Extended Data Fig.3f-3` | `A3:B10`, 8 observations, Young/Aged measurements |
| `chit1_ext3c_2.csv` | `Extended Data Fig.3c-2` | `A3:B10`, 8 observations, Young/Aged measurements |
| `chit1_ext3f_2.csv` | `Extended Data Fig.3f-2` | `A3:B10`, 8 observations, Young/Aged measurements |

CSV numeric values are unchanged. Column headers were renamed for clarity; separate statistical annotation columns are omitted. Source and CSV SHA-256 checksums are in `provenance.json`. `tools/extract_demo.py` reproduces the excerpts.

Original workbooks are present locally in `data/raw/`, excluded from Git/package builds:

- [Source Data Fig. 2](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-023-06783-1/MediaObjects/41586_2023_6783_MOESM5_ESM.xlsx).
- [Source Data Extended Data Fig. 3](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-023-06783-1/MediaObjects/41586_2023_6783_MOESM11_ESM.xlsx).
- [Source Data Extended Data Fig. 5](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-023-06783-1/MediaObjects/41586_2023_6783_MOESM12_ESM.xlsx).

The article is under exclusive licence to Springer Nature. The distribution includes only a small factual numeric excerpt with attribution, not the publisher's workbook, prose or figures. No separate open licence for the full workbooks has been established.

Run `python examples/demo.py` after installing the project. It analyzes the identical packaged copies of these CSVs and writes `reports/demo_report.txt` and `reports/demo_report.json`. The explicitly configured 100% row-total check reports **100.3%** for the second observation of `Fig.2b-1`; it does not infer the cause.

The demo also finds the eight identical Aged values and seven consecutive identical Young values between Fig.2b-2 and Extended Data Fig.3f-3. Between P2RY12-negative and MS4A7-positive percentages, 14 of 16 differences lie on a 0.1 grid; the two exceptions are shown explicitly. These are numerical observations, not independent evidence counts or a misconduct verdict.
