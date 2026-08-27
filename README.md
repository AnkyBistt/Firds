# FIRDS DLTINS Reference Data Inspector & Reconciler

A high-performance Python console application & CLI tool to inspect, search, and reconcile **ESMA (EU)** and **FCA (UK)** Financial Instruments Reference Data System (**FIRDS**) DLTINS (`auth.036.001.02`) XML files.

Designed specifically to diagnose and troubleshoot **why certain ISINs get missed or dropped during daily delta ingestion** across different environment databases.

---

## Features

- 🚀 **Zero-Memory Streaming Parser**: Uses memory-safe `iterparse` to parse multi-gigabyte DLTINS XML and `.zip` archives directly without extracting to disk.
- 🇪🇺 🇬🇧 **Dual-Region Support (EU & UK)**:
  - **ESMA (EU)**: Direct integration with ESMA Solr API for automatic search, download, and caching.
  - **FCA (UK)**: Local directory and cache scanner with custom feed support.
- 🔍 **Root-Cause Diagnostic Engine**: Automatically detects why records are dropped by ingestion pipelines:
  - Record types (`CANC` cancellations, `TERMN` terminations)
  - Missing mandatory attributes (Missing Issuer LEI, missing CFI code)
  - Expired trading venue termination dates
  - Multi-venue listing ambiguities
- ⚖️ **Side-by-Side Reconciliation (Diff)**:
  - Compares an ISIN between **EU vs UK** DLTINS files.
  - Compares DLTINS raw source records directly against **Database (SQLite/Postgres)** ingested rows.
- 🏷️ **ISO 10962 CFI Code Decoder**: Decodes 6-letter CFI codes (e.g. `ESVUFR`, `DBFTFR`, `OCAFPS`) into descriptive category and attribute breakdowns.
- 📊 **Rich Console & Export**: Color-coded tables, status badges, diagnostics panels, and instant export to **JSON, CSV, or Markdown**.
- 🧙 **Interactive CLI Wizard**: Run `python firds_tool.py --interactive` for a guided step-by-step experience.

---

## Installation

```bash
cd firds_inspector
pip install -r requirements.txt
```

### Dependencies
- `rich` (Terminal formatting and tables)
- `requests` (ESMA Solr API client)
- `python-dateutil` (Date parsing)

---

## Usage Guide

### 1. Single ISIN Lookup
Inspect all attributes and trading venues for a specific ISIN on a given date:
```bash
python firds_tool.py --isin US0378331005 --region eu --date 2024-01-15
```

### 2. Compare EU vs UK (Reconciliation Diff)
Compare how an ISIN is represented in ESMA (EU) versus FCA (UK) files to spot discrepancies:
```bash
python firds_tool.py --isin US0378331005 --compare --date 2024-01-15
```

### 3. Compare DLTINS Source vs Environment Database
Verify whether an ISIN in the raw DLTINS file matches what was inserted into your local database table:
```bash
python firds_tool.py --isin US0378331005 --sqlite-db /path/to/environment.db --date 2024-01-15
```

### 4. Batch ISIN Reconciliation
Check a whole list of missing ISINs from a text file (one ISIN per line):
```bash
python firds_tool.py --file missing_isins.txt --region eu --date 2024-01-15
```

### 5. Filter & Search by CFI Code or Trading Venue MIC
Search for all Debt instruments (`DB...`) on venue `XBER`:
```bash
python firds_tool.py --cfi-filter DB --mic-filter XBER --region eu --date 2024-01-15
```

### 6. Export Results
Export search or diff results to JSON, CSV, or Markdown:
```bash
# Export to JSON
python firds_tool.py --isin US0378331005 --region eu --export-json apple_firds.json

# Export to CSV
python firds_tool.py --cfi-filter ES --region eu --export-csv equities_firds.csv

# Export Diff Report to Markdown
python firds_tool.py --isin US0378331005 --compare --export-md diff_report.md
```

### 7. Interactive Guided Mode
Simply run without arguments or with `--interactive`:
```bash
python firds_tool.py --interactive
```

---

## Common Ingestion Failure Reasons (Diagnostics)

| Diagnostic Flag | Root Cause | Impact on Database Ingestion |
| --- | --- | --- |
| `[WARNING] Record type is 'CANC'` | Record is an explicit cancellation in DLTINS delta. | Ingestion pipeline may purge or skip the record. |
| `[WARNING] Record type is 'TERMN'` | Record is a termination event. | Instrument may be marked inactive. |
| `[CAUTION] Issuer LEI is missing` | Issuer tag `<Issr>` is absent in XML. | DB `NOT NULL` or foreign key constraints cause insertion rollback. |
| `[CAUTION] CFI code is missing` | `<ClssfctnFinInstrm>` tag is missing. | Classification-based ingestion pipeline rejects row. |
| `[NOTE] Expired termination date` | `<TermntnDt>` is earlier than report date. | Filtered out by active instrument queries. |
| `[INFO] Multi-listed venue` | Instrument has multiple `<TradgVnAttrbts>` tags. | Venue mapping conflicts if DB only allows 1 venue per ISIN. |

---

## Running Tests

Execute the automated unit test suite:
```bash
python -m unittest discover -s tests
```
