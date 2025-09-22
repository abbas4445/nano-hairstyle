# Nano Hairstyle Studio

## Overview
Nano Hairstyle Studio pairs a FastAPI backend with a Streamlit interface so that users can upload a portrait and generate alternative hairstyles. The Streamlit app lives in `streamlit_app.py` and calls the FastAPI service via the `FASTAPI_BASE_URL` setting.

## Previewing the frontend locally
1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies: `pip install -r requirements.txt`.
3. Set the backend URL (default is `http://127.0.0.1:8000`):
   - PowerShell: `$env:FASTAPI_BASE_URL="https://your-cloud-run-url"`
   - Bash: `export FASTAPI_BASE_URL="https://your-cloud-run-url"`
4. Launch the UI: `streamlit run streamlit_app.py`.

## Deploying the Streamlit app
Streamlit Community Cloud pulls code from your Git repository and installs `requirements.txt` automatically.

1. Push this project to GitHub (or another git host supported by Streamlit Cloud).
2. In the Streamlit Cloud dashboard, choose **Deploy an app**, select the repository and branch, and set the main file to `streamlit_app.py`.
3. Under **Advanced settings -> Secrets**, add the backend URL so the app can reach your Cloud Run service. Create a `FASTAPI_BASE_URL` entry pointing at the public HTTPS endpoint. Example secrets file:

```toml
FASTAPI_BASE_URL = "https://nano-hairstyle-xxxxx.a.run.app"
MAX_STREAM_COUNT = "6"  # optional override
```

4. Click **Deploy**. Streamlit installs the dependencies and starts the app automatically. Subsequent pushes to the selected branch trigger a redeploy.

### During development
- Use the sidebar field labeled "FastAPI base URL" to switch between backends without redeploying.
- The "Number of hairstyles" input is capped by the `MAX_STREAM_COUNT` environment variable (default 6). Tuning it in secrets helps prevent overly long Cloud Run requests.
- Streamlit logs (View -> Logs) are helpful for debugging connection issues with the backend.

## Backend expectations
The frontend calls two endpoints:
- `POST /hairstyle` for single-image responses.
- `POST /hairstyles/stream` for newline-delimited JSON streaming.

Ensure the Cloud Run service enables unauthenticated HTTPS requests or configure authentication and update the Streamlit app accordingly.
