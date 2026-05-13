# Value Stock Screener — Setup Guide

## What's in this repo

| File | Purpose |
|------|---------|
| `scan.py` | Python script — scans FTSE All-Share via yfinance, outputs `data.json` |
| `.github/workflows/scan.yml` | GitHub Actions — runs `scan.py` weekly, auto-commits `data.json` |
| `StockScreener.jsx` | React component — paste into Figma Sites as a code layer |
| `data.json` | Auto-generated output — do not edit manually |

---

## One-time setup (takes ~15 minutes)

### Step 1 — Create a GitHub repository

1. Go to [github.com](https://github.com) and create a new **public** repository
   (e.g. `stock-screener`)
2. Upload all files from this folder into the repo root, keeping the
   `.github/workflows/` folder structure intact

### Step 2 — Enable GitHub Pages

1. In your repo, go to **Settings → Pages**
2. Under *Source*, select **Deploy from a branch**
3. Choose branch: `main`, folder: `/ (root)`
4. Click **Save**
5. Your `data.json` will be publicly accessible at:
   ```
   https://<your-username>.github.io/<your-repo-name>/data.json
   ```

### Step 3 — Update the DATA_URL in StockScreener.jsx

Open `StockScreener.jsx` and replace line 7:
```js
const DATA_URL = "https://<your-username>.github.io/<your-repo-name>/data.json";
```
with your actual URL, e.g.:
```js
const DATA_URL = "https://johndoe.github.io/stock-screener/data.json";
```

### Step 4 — Run the first scan manually

1. In your GitHub repo, go to **Actions → Weekly Stock Scan**
2. Click **Run workflow → Run workflow**
3. Wait ~20–40 minutes for it to complete
4. Check that `data.json` has been committed to the repo

> **Note:** The first run may take longer as yfinance fetches data for ~600 tickers.
> Subsequent runs will be similar in duration.

### Step 5 — Add the component to Figma Sites

1. Open your Figma Sites file
2. In the left panel, click **Insert → Code layer** (or use the AI chat to add a code layer)
3. Delete the placeholder code and paste the entire contents of `StockScreener.jsx`
4. The component should render a live stock screener pulling from your `data.json`

---

## Weekly automation

Once set up, GitHub Actions runs every **Sunday at 06:00 UTC** automatically.
No manual work required. You can also trigger a manual run any time via
**Actions → Weekly Stock Scan → Run workflow**.

---

## Adjusting default criteria

To change the default screening criteria (the values sliders start at),
edit the constants at the top of `scan.py`:

```python
MAX_PE        = 20    # Maximum P/E ratio
MAX_PB        = 5     # Maximum P/B ratio
MIN_CURRENT   = 1     # Minimum current ratio
MIN_ROE       = 10    # Minimum 5-year average ROE (%)
```

Users of the web app can also adjust these interactively via the sliders —
their changes filter the already-scanned data client-side without re-running
the Python script.

---

## Adding NYSE / Nasdaq later

When you're ready to expand beyond FTSE All-Share:

1. Add a `get_nyse_tickers()` and/or `get_nasdaq_tickers()` function to `scan.py`
2. Call them in `run_scan()` and add results to `build_output()`
3. The React component already has the exchange dropdown ready — just ensure
   `data.json` has `nyse` and `nasdaq` arrays populated

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `data.json` not loading in Figma | Check DATA_URL is correct and GitHub Pages is enabled |
| GitHub Action failing | Check the Actions log; usually a yfinance rate-limit — re-run manually |
| No stocks passing filters | yfinance data gaps are common; try relaxing criteria |
| Figma Sites CORS error | Ensure the repo is public so the JSON URL is accessible |
