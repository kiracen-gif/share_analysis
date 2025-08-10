# Stock Insight App (Streamlit)

A browser-based stock analysis app. Enter a ticker/code to get industry pulse, valuation, technicals (MACD/KDJ), news digest, and export an Excel report.

## Quick start (local)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1) Push this folder to GitHub.  
2) Go to https://share.streamlit.io → New app → select repo → main file `app.py`.  
3) Deploy. Done.

## Docker (Render/Cloud Run)
```bash
docker build -t stockapp:latest .
docker run -p 8501:8501 stockapp:latest
```

## Notes
- Uses `akshare` for CN markets. Falls back to `yfinance` for global symbols if `akshare` not present.
- Includes rate-limit friendly retries and graceful data fallbacks.
- Excel export uses in-memory buffer; no disk writes required on PaaS.
