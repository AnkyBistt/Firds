# FIRDS Reference Data Web API & DLTINS Inspector

A production-ready **FastAPI Web Service** and CLI tool to query, inspect, and reconcile **ESMA (EU)** and **FCA (UK)** Financial Instruments Reference Data System (**FIRDS**) DLTINS (`auth.036.001.02` & `auth.036.001.03`) XML reference data.

Configured for **Render's free tier** cloud deployment and local development.

---

## 🚀 Features

- ⚡ **Production-Ready FastAPI Web API**: High-performance asynchronous REST API with automatic interactive OpenAPI / Swagger documentation (`/docs`).
- 🌐 **Live Regulatory Ingestion**: Queries the official ESMA Solr API on demand, downloads, and streams reference data for any given publication date.
- 💾 **Low-Memory Streaming Parser**: Zero-memory `iterparse` engine designed specifically for cloud environments with limited RAM (e.g. Render 512MB free tier), streaming multi-gigabyte XML and `.zip` archives directly without disk inflation.
- 🛡️ **Comprehensive Validation & Error Handling**: Returns clean, typed JSON responses and standard HTTP status codes (`200 OK`, `400 Bad Request`, `404 Not Found`, `502 Bad Gateway`).
- 🏷️ **ISO 10962 CFI Code Decoder**: Automatically decodes 6-letter CFI codes (e.g. `DCVGFB`, `ESVUFR`, `DBFTFR`) into descriptive asset classifications.
- ⚖️ **Cross-Region Diff & Diagnostics**: Compares how instruments are reported in ESMA vs FCA and diagnoses ingestion failure root causes.
- ☁️ **Render Free Tier Ready**: Fully configured with `render.yaml`, `$PORT` binding on `0.0.0.0`, ephemeral cache directory `/tmp/firds_cache`, and health check endpoint `/health`.

---

## 🛠️ API Endpoints

### 1. `GET /search`
Searches for instrument reference data by ISIN, publication date, and region.

* **Query Parameters:**
  - `isin` *(required)*: 12-character ISO 6166 ISIN (e.g. `AT0000A0SL91`, `US0378331005`)
  - `date` *(required)*: Publication Date in `YYYY-MM-DD` format (e.g. `2024-01-15`)
  - `region` *(optional, default: `EU`)*: Regulatory region (`EU`, `UK`, or `ALL`)
  - `dltins_dir` *(optional)*: Local custom directory containing DLTINS files (e.g. `sample_data`)

* **Example Request:**
  ```http
  GET /search?isin=AT0000A0SL91&date=2024-01-15&region=EU
  ```

* **Example 200 OK JSON Response:**
  ```json
  {
    "success": true,
    "query_isin": "AT0000A0SL91",
    "date": "2024-01-15",
    "region": "EU",
    "count": 1,
    "instruments": [
      {
        "isin": "AT0000A0SL91",
        "region": "EU",
        "record_type": "MODI",
        "source_file": "DLTINS_20240115_01of01.zip::DLTINS_20240115_01of01.xml",
        "general": {
          "isin": "AT0000A0SL91",
          "full_name": "HYPOBK 4 01/12/24 BOND",
          "short_name": "HYP WBBK/SU CV BD 20240112 3 GTD",
          "cfi_code": "DCVGFB",
          "cfi_description": "Debt Instruments -> Convertible Bonds (Interest: Variable/Floating rate, Guarantee: Guaranteed, Redemption: Fixed maturity, Form: Bearer)",
          "currency": "EUR",
          "commodity_derivative_indicator": false,
          "issuer_lei": "5299003LP3FEIX2HYD09",
          "custom_attributes": {}
        },
        "trading_venues": [
          {
            "mic": "BTFE",
            "issuer_request": false,
            "first_trade_date": "2021-09-09T15:07:31.346Z",
            "termination_date": "9999-12-31T23:59:59.999Z",
            "admission_approval_date": null,
            "request_for_admission_date": null,
            "custom_attributes": {}
          }
        ],
        "technical": {
          "relevant_competent_authority": "AT",
          "publication_date": "2024-01-15",
          "record_date": null
        }
      }
    ]
  }
  ```

---

### 2. `GET /compare`
Compares an ISIN side-by-side between **ESMA (EU)** and **FCA (UK)** feeds and diagnoses ingestion root-cause issues.

* **Example Request:**
  ```http
  GET /compare?isin=US0378331005&date=2024-01-15&dltins_dir=sample_data
  ```

---

### 3. `GET /health`
Health check endpoint for Render and uptime monitoring.

* **Example Response:**
  ```json
  {
    "status": "ok",
    "service": "firds-reference-data-api",
    "version": "1.0.0",
    "cache_directory": "/tmp/firds_cache/eu"
  }
  ```

---

### 4. `GET /docs`
Interactive Swagger UI allowing you to test all endpoints directly in your browser.

---

## 💻 Local Development & Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Web Server Locally
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser at **`http://localhost:8000/docs`** to test the API.

### 3. Run Automated Tests
```bash
python -m unittest discover -s tests
```

---

## ☁️ Deployment on Render (Free Tier)

### Method A: Deploy via Render Blueprint (Recommended)
1. Push your repository to GitHub: `https://github.com/AnkyBistt/Firds`
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** -> **Blueprint**.
4. Connect your GitHub repository `Firds`.
5. Render will automatically read `render.yaml` and configure the Web Service with the correct build and start commands.

### Method B: Manual Web Service Setup on Render
1. Click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following fields:
   - **Name**: `firds-reference-data-api`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.12.4`
   - `FIRDS_CACHE_DIR`: `/tmp/firds_cache`
   - `ESMA_SOLR_URL`: `https://registers.esma.europa.eu/solr/esma_registers_firds_files/select`
   - `FIRDS_DATA_DIR`: `sample_data`
5. Click **Deploy Web Service**.

---

## ⚙️ Environment Variables Reference

| Variable | Default Value | Description |
| --- | --- | --- |
| `PORT` | `8000` | Port for Uvicorn server (automatically set by Render). |
| `HOST` | `0.0.0.0` | Host IP binding. |
| `FIRDS_CACHE_DIR` | `/tmp/firds_cache` | Path for downloaded DLTINS files (uses ephemeral disk on Render). |
| `ESMA_SOLR_URL` | `https://registers.esma.europa.eu/solr/...` | Base Solr endpoint for ESMA FIRDS registers. |
| `ESMA_TIMEOUT_SECONDS`| `30` | Timeout in seconds for ESMA API downloads. |
| `FIRDS_DATA_DIR` | `sample_data` | Default directory for bundled/offline DLTINS files. |

---

## ⚠️ Render Free Tier Notes & Limitations

- **Cold Starts**: Render's free tier spins down web services after 15 minutes of inactivity. The first request after spindown may take 30–50 seconds while the container boots up. Subsequent requests respond immediately.
- **512MB RAM Constraint**: Our streaming `iterparse` engine maintains a constant memory footprint (~25MB–40MB) while processing 500MB+ XML archives, staying well within Render's 512MB limit.
- **Ephemeral Storage**: Downloaded DLTINS zip files in `/tmp/firds_cache` are cached during the container instance lifecycle. If the instance restarts, it will redownload files from ESMA on demand.
