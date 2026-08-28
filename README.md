# FIRDS Reference Data Web API & DLTINS Inspector

A production-ready **FastAPI Web Service** and CLI tool to query, inspect, and reconcile **ESMA (EU)** and **FCA (UK)** Financial Instruments Reference Data System (**FIRDS**) DLTINS (`auth.036.001.02` & `auth.036.001.03`) XML reference data.

---

## 🌐 Live Service & Interactive Swagger Documentation

* **Interactive Swagger UI**: [https://firds.onrender.com/docs](https://firds.onrender.com/docs)
* **Alternative Redoc Docs**: [https://firds.onrender.com/redoc](https://firds.onrender.com/redoc)
* **Base API URL**: [https://firds.onrender.com/](https://firds.onrender.com/)
* **Health Check**: [https://firds.onrender.com/health](https://firds.onrender.com/health)

---

## 🚀 Key Capabilities

- ⚡ **Interactive Swagger & OpenAPI 3.0**: Fully documented REST API with typed JSON request/response schemas and instant test sandbox (`/docs`).
- 🔍 **Direct ISIN Lookup (No Date Required)**: Queries the official live **ESMA Master FIRDS Database** (`esma_registers_firds` Solr core) to fetch instrument details across all European trading venues.
- 📅 **Date-Specific DLTINS Stream Parser**: Streams daily DLTINS `.zip` and `.xml` files directly from regulatory registers with a constant 25MB–40MB RAM footprint (`ET.iterparse`).
- ⚖️ **Cross-Region Reconciliation (EU vs UK)**: Field-by-field diff engine with automatic root-cause diagnostics for missing ISINs.
- 🏷️ **ISO 10962 CFI Decoder**: Decodes 6-letter CFI codes (e.g. `ESVUFR`, `DCVGFB`, `DBFTFR`) into human-readable classifications.
- ☁️ **Cloud Native (Render Free Tier)**: Configured with `render.yaml`, `$PORT` dynamic binding, and ephemeral cache `/tmp/firds_cache`.

---

## 🛠️ API Reference & Usage

### 1. Direct ISIN Lookup (No Date Required)
Query the live master FIRDS register for an ISIN. Returns all European trading venues, CFI classifications, issuer LEI, and status.

```http
GET /lookup?isin={ISIN}&region={EU|UK}
GET /isin/{ISIN}
```

#### Example:
* `GET https://firds.onrender.com/isin/GB0002634946`
* `GET https://firds.onrender.com/lookup?isin=US0378331005`

#### Sample JSON Response:
```json
{
  "success": true,
  "query_isin": "GB0002634946",
  "region": "EU",
  "source": "ESMA FIRDS Master Register (Live Solr Database)",
  "count": 1,
  "instruments": [
    {
      "isin": "GB0002634946",
      "region": "EU",
      "record_type": "NEWT",
      "source_file": "ESMA FIRDS Master Register (Live Solr Database)",
      "general": {
        "isin": "GB0002634946",
        "full_name": "BAE SYSTEMS PLC",
        "short_name": "BAE SYSTEMS/ORD 2.5P",
        "cfi_code": "ESVUFR",
        "cfi_description": "Equities -> Common / Ordinary Shares (Voting: Voting, Transfer: Free/Unrestricted, Payment: Fully Paid, Form: Registered)",
        "currency": "GBP",
        "commodity_derivative_indicator": false,
        "issuer_lei": "2138001V2A89AQWS3O48",
        "custom_attributes": {}
      },
      "trading_venues": [
        {
          "mic": "XLON",
          "issuer_request": true,
          "first_trade_date": "1981-02-17T00:00:00Z",
          "termination_date": null,
          "admission_approval_date": "1981-02-17T00:00:00Z",
          "request_for_admission_date": null,
          "custom_attributes": {
            "status": "Active"
          }
        }
      ],
      "technical": {
        "relevant_competent_authority": "GB",
        "publication_date": "2026-08-23T01:01:57.643Z"
      }
    }
  ]
}
```

---

### 2. Search by Date & Region
Search within a specific publication date's DLTINS XML file feed.

```http
GET /search?isin={ISIN}&date={YYYY-MM-DD}&region={EU|UK|ALL}
```

#### Example:
* `GET https://firds.onrender.com/search?isin=AT0000A0SL91&date=2024-01-15&region=EU`
* `GET https://firds.onrender.com/search?isin=US0378331005&date=2024-01-15&region=EU&dltins_dir=sample_data`

---

### 3. Cross-Region Reconciliation Diff
Compares an ISIN between **ESMA (EU)** and **FCA (UK)** feeds and highlights field differences and ingestion root-cause diagnostics.

```http
GET /compare?isin={ISIN}&date={YYYY-MM-DD}
```

#### Example:
* `GET https://firds.onrender.com/compare?isin=US0378331005&date=2024-01-15&dltins_dir=sample_data`

---

## 🔍 How to Identify ESMA (EU) vs FCA (UK) Data

| Response Field | If from ESMA (EU) | If from FCA (UK) |
| --- | --- | --- |
| **`region`** | `"EU"` | `"UK"` |
| **`source`** | `"ESMA FIRDS Master Register"` or `DLTINS_..._EU.xml` | `"FCA (UK) FIRDS"` or `DLTINS_..._UK.xml` |
| **`technical.relevant_competent_authority`** | `"DE"` (BaFin), `"FR"` (AMF), `"NL"` (AFM), `"AT"` (FMA) | `"GB"` (FCA UK) |
| **`trading_venues[].mic`** | `XPAR` (Paris), `XETR` (Frankfurt), `XAMS` (Amsterdam) | `XLON` (London), `BATE` (Cboe UK), `CHIX` (Chi-X UK), `AQSE` (Aquis) |

---

## 🧩 Reconciling Missing ISINs with Audit Tables

If your daily ingestion audit table records a count mismatch (`rows_affected_in_db < count_in_file`):

1. **Check Upstream Lifecycle Record**: Query `/lookup?isin={ISIN}` to check `record_type`:
   - `CANC`: Cancelled by regulator.
   - `TERMN`: Terminated / Expired venue trading.
2. **Check Multi-Venue Overwrites**: Verify if the ISIN trades on multiple MICs (`XNAS`, `XFRA`, `XLON`). If your database primary key is `isin` instead of `(isin, mic)`, multiple venues will collapse into a single row.
3. **Batch Export Reconciliation**:
   ```cmd
   python firds_tool.py --file missing_isins.txt --compare --date 2024-01-15 --export-md reconciliation_report.md
   ```

---

## 💻 Local CLI & Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Local Web Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000/docs`** to test all endpoints.

### 3. CLI Commands
```cmd
# Direct ISIN lookup
python firds_tool.py --isin GB0002634946

# Date-specific search
python firds_tool.py --isin AT0000A0SL91 --date 2024-01-15 --region EU

# Compare EU vs UK
python firds_tool.py --isin US0378331005 --compare --date 2024-01-15 --dltins-dir sample_data

# Interactive Wizard
python firds_tool.py --interactive
```

### 4. Run Automated Test Suite
```bash
python -m unittest discover -s tests
```

---

## ☁️ Render Deployment Guide

### Automatic Deploy via Blueprint:
1. Connect repository `https://github.com/AnkyBistt/Firds` to [Render Dashboard](https://dashboard.render.com/).
2. Render reads `render.yaml` and deploys automatically:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `PYTHON_VERSION`: `3.12.4`
     - `FIRDS_CACHE_DIR`: `/tmp/firds_cache`
     - `ESMA_SOLR_URL`: `https://registers.esma.europa.eu/solr/esma_registers_firds_files/select`
