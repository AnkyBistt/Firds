# FIRDS DLTINS Reference Data Inspector & Reconciler

A high-performance Python console application & CLI tool to inspect, search, and reconcile **ESMA (EU)** and **FCA (UK)** Financial Instruments Reference Data System (**FIRDS**) DLTINS (`auth.036.001.02` & `auth.036.001.03`) XML files.

Designed specifically to diagnose and troubleshoot **why certain ISINs get missed or dropped during daily delta ingestion** across different environment databases.

---

## ⚡ Quick Start: How to Run the App

### 1. Prerequisites & Setup
Ensure you have Python 3.8+ installed.

```bash
# Clone the repository (if not already cloned)
git clone https://github.com/AnkyBistt/Firds.git
cd Firds

# Install dependencies
pip install -r requirements.txt
```

---

### 2. Run Modes

#### 🧙 Mode A: Interactive Guided Wizard (Recommended)
Launch the step-by-step interactive wizard without memorizing flags:
```bash
python firds_tool.py --interactive
```
*(Or simply run `python firds_tool.py` without arguments)*

---

#### 🌐 Mode B: Query Live Data from ESMA Registers API
To query reference data directly from the live ESMA Solr feed for any publication date:
```bash
# Query an ISIN live from ESMA (downloads and caches DLTINS zip automatically)
python firds_tool.py --isin AT0000A0SL91 --region eu --date 2024-01-15

# Search live debt instruments published on that date
python firds_tool.py --cfi-filter DC --region eu --date 2024-01-15

# Search live equities published on that date
python firds_tool.py --cfi-filter ES --region eu --date 2024-01-15
```

---

#### 📁 Mode C: Query Against Local Downloaded DLTINS Files
If your daily ingestion service downloads DLTINS files into a local folder:
```bash
# Point to your local DLTINS folder
python firds_tool.py --isin US0378331005 --region eu --dltins-dir "C:\path\to\dltins_folder"

# Test with included sample files
python firds_tool.py --isin US0378331005 --region eu --date 2024-01-15 --dltins-dir sample_data
```

---

#### ⚖️ Mode D: Cross-Region Reconciliation (EU vs UK Diff)
Compare how an ISIN is reported in ESMA (EU) versus FCA (UK) files to spot discrepancies and root causes:
```bash
python firds_tool.py --isin US0378331005 --compare --date 2024-01-15 --dltins-dir sample_data
```

---

#### 🗄️ Mode E: Compare DLTINS Source vs Ingested Database
Verify whether an ISIN in the raw DLTINS file matches what was inserted into your local database:
```bash
python firds_tool.py --isin US0378331005 --sqlite-db "C:\path\to\environment.db" --date 2024-01-15
```

---

#### 📋 Mode F: Batch Reconcile Multiple Missing ISINs
Pass a `.txt` file containing ISINs (one per line) to verify a list of missing instruments:
```bash
python firds_tool.py --file missing_isins.txt --region eu --date 2024-01-15
```

---

#### 📤 Mode G: Export Results
Export parsed instrument details or diff reports:
```bash
# Export search results to JSON
python firds_tool.py --isin US0378331005 --region eu --export-json result.json --dltins-dir sample_data

# Export instruments list to CSV
python firds_tool.py --cfi-filter ES --region eu --export-csv equities.csv --dltins-dir sample_data

# Export Diff Reconciliation Report to Markdown
python firds_tool.py --isin US0378331005 --compare --export-md diff_report.md --dltins-dir sample_data
```

---

## 🛠️ CLI Arguments Reference

| Argument | Description | Example |
| --- | --- | --- |
| `--interactive` | Launch interactive step-by-step console wizard. | `python firds_tool.py --interactive` |
| `--isin <ISIN>` | Single 12-character ISIN to lookup. | `--isin US0378331005` |
| `--region <EU\|UK\|ALL>` | Target regulatory region (Default: `EU`). | `--region EU` |
| `--date <YYYY-MM-DD>` | Publication Date (Default: Today). | `--date 2024-01-15` |
| `--compare` | Compare ISIN between EU and UK DLTINS files. | `--compare` |
| `--dltins-dir <path>` | Path to local directory with `.zip` or `.xml` files. | `--dltins-dir ./sample_data` |
| `--sqlite-db <path>` | Path to SQLite DB to compare raw file vs ingested DB. | `--sqlite-db ./app.db` |
| `--file <path>` | Text file containing list of ISINs for batch check. | `--file ./isins.txt` |
| `--cfi-filter <prefix>` | Filter instruments by ISO 10962 CFI code prefix. | `--cfi-filter DB` |
| `--mic-filter <MIC>` | Filter instruments by Trading Venue MIC. | `--mic-filter XNAS` |
| `--export-json <path>` | Export output to structured JSON. | `--export-json out.json` |
| `--export-csv <path>` | Export output to CSV. | `--export-csv out.csv` |
| `--export-md <path>` | Export reconciliation report to Markdown. | `--export-md out.md` |
| `-v`, `--verbose` | Enable verbose debug logs. | `-v` |

---

## 🔍 Ingestion Failure Root-Cause Diagnostics

When comparing records or inspecting problematic instruments, the tool automatically runs root-cause analysis:

| Diagnostic Flag | Root Cause | Impact on Database Ingestion |
| --- | --- | --- |
| `[WARNING] Record type is 'CANC'` | Record is an explicit cancellation in DLTINS delta. | Ingestion pipeline may purge or skip the record. |
| `[WARNING] Record type is 'TERMN'` | Record is a termination event. | Instrument may be marked inactive. |
| `[CAUTION] Issuer LEI is missing` | Issuer tag `<Issr>` is absent in XML. | DB `NOT NULL` or foreign key constraints cause insertion rollback. |
| `[CAUTION] CFI code is missing` | `<ClssfctnFinInstrm>` tag is missing. | Classification-based ingestion pipeline rejects row. |
| `[NOTE] Expired termination date` | `<TermntnDt>` is earlier than report date. | Filtered out by active instrument queries. |
| `[INFO] Multi-listed venue` | Instrument has multiple `<TradgVnAttrbts>` tags. | Venue mapping conflicts if DB only allows 1 venue per ISIN. |

---

## 🧪 Running Automated Tests

Run the unit test suite covering XML streaming, CFI decoding, and reconciliation diffs:

```bash
python -m unittest discover -s tests
```
