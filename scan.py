"""
FTSE All-Share Stock Screener
Fetches financial data via yfinance and outputs data.json

Criteria (defaults, can be overridden via env vars):
  - Max PE Ratio: 20
  - Max PB Ratio: 5
  - Current Ratio > 1
  - 5-Year Average ROE > 10%

Usage:
  pip install yfinance pandas requests
  python scan.py
"""

import yfinance as yf
import pandas as pd
import json
import time
import requests
import os
from datetime import datetime

# ── Screening criteria (override via environment variables) ──────────────────
MAX_PE        = float(os.getenv("MAX_PE", 20))
MAX_PB        = float(os.getenv("MAX_PB", 5))
MIN_CURRENT   = float(os.getenv("MIN_CURRENT_RATIO", 1))
MIN_ROE       = float(os.getenv("MIN_ROE_5Y", 10))   # percent

# ── Output path ──────────────────────────────────────────────────────────────
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "data.json")

# ── Fetch FTSE All-Share tickers ─────────────────────────────────────────────
def get_ftse_allshare_tickers():
    """
    Returns a list of FTSE All-Share tickers in yfinance format (e.g. BARC.L).
    Uses a curated public source; falls back to a hardcoded FTSE 100 list
    if the network request fails.
    """
    print("Fetching FTSE All-Share ticker list...")

    # Primary: Wikipedia FTSE 100 + FTSE 250 constituent tables
    tickers = set()

    urls = {
        "FTSE 100":  "https://en.wikipedia.org/wiki/FTSE_100_Index",
        "FTSE 250":  "https://en.wikipedia.org/wiki/FTSE_250_Index",
        "FTSE SmallCap": "https://en.wikipedia.org/wiki/FTSE_SmallCap_Index",
    }

    for name, url in urls.items():
        try:
            tables = pd.read_html(url, attrs={"id": "constituents"})
            if tables:
                df = tables[0]
                # Column is usually 'Ticker' or 'EPIC' or 'Symbol'
                for col in ["Ticker", "EPIC", "Symbol", "ticker"]:
                    if col in df.columns:
                        raw = df[col].dropna().tolist()
                        for t in raw:
                            t = str(t).strip().upper()
                            # Wikipedia uses dots; yfinance uses dots too for .L
                            if not t.endswith(".L"):
                                t = t + ".L"
                            tickers.add(t)
                        print(f"  {name}: {len(raw)} tickers loaded")
                        break
        except Exception as e:
            print(f"  Warning: Could not load {name} from Wikipedia: {e}")

    if not tickers:
        print("  Falling back to hardcoded FTSE 100 ticker list...")
        tickers = set(FTSE100_FALLBACK)

    result = sorted(tickers)
    print(f"Total tickers to scan: {len(result)}")
    return result


# ── Hardcoded FTSE 100 fallback (as of 2024) ─────────────────────────────────
FTSE100_FALLBACK = [
    "AAF.L","AAL.L","ABF.L","ADM.L","AHT.L","ANTO.L","AZN.L","BA.L","BARC.L",
    "BATS.L","BDEV.L","BEZ.L","BKG.L","BME.L","BNZL.L","BP.L","BRBY.L","BT-A.L",
    "CCH.L","CNA.L","CPG.L","CRDA.L","DCC.L","DGE.L","DPLM.L","EDV.L","ENT.L",
    "EXPN.L","EZJ.L","FCIT.L","FERG.L","FLTR.L","FRES.L","GBPOUND.L","GLEN.L",
    "GSK.L","HIK.L","HL.L","HLMA.L","HLN.L","HSBA.L","HSX.L","IAG.L","ICG.L",
    "IHG.L","III.L","IMB.L","INF.L","ITRK.L","JD.L","KGF.L","LAND.L","LGEN.L",
    "LLOY.L","LMP.L","LSEG.L","MKS.L","MNDI.L","MNG.L","MRO.L","NG.L","NWG.L",
    "NXT.L","OCDO.L","PHNX.L","PRU.L","PSH.L","PSN.L","PSON.L","RB.L","REC.L",
    "RELX.L","RIO.L","RKT.L","RMV.L","RR.L","RS1.L","RSA.L","RTO.L","SBRY.L",
    "SDR.L","SGE.L","SGRO.L","SJP.L","SKG.L","SMDS.L","SMIN.L","SMT.L","SN.L",
    "SPX.L","SSE.L","STAN.L","STJ.L","SVT.L","TBCG.L","TSCO.L","TW.L","ULVR.L",
    "UTG.L","UU.L","VOD.L","WEIR.L","WPP.L","WTB.L",
]


# ── Compute 5-year average ROE ────────────────────────────────────────────────
def get_5y_avg_roe(ticker_obj):
    """
    Pulls annual income statement + balance sheet and computes
    average ROE over up to 5 years. Returns None if insufficient data.
    """
    try:
        income = ticker_obj.financials          # annual, columns = fiscal year dates
        balance = ticker_obj.balance_sheet

        if income is None or balance is None:
            return None
        if income.empty or balance.empty:
            return None

        net_income_row = None
        for label in ["Net Income", "Net Income Common Stockholders"]:
            if label in income.index:
                net_income_row = income.loc[label]
                break

        equity_row = None
        for label in ["Stockholders Equity", "Common Stock Equity", "Total Stockholders Equity"]:
            if label in balance.index:
                equity_row = balance.loc[label]
                break

        if net_income_row is None or equity_row is None:
            return None

        # Align on common years
        common_years = net_income_row.index.intersection(equity_row.index)
        if len(common_years) == 0:
            return None

        roe_values = []
        for year in sorted(common_years, reverse=True)[:5]:
            ni = net_income_row[year]
            eq = equity_row[year]
            if eq and eq != 0 and ni is not None:
                roe_values.append((ni / eq) * 100)

        if not roe_values:
            return None

        return sum(roe_values) / len(roe_values)

    except Exception:
        return None


# ── Screen a single ticker ────────────────────────────────────────────────────
def screen_ticker(symbol):
    """
    Fetches data for one ticker and returns a dict if it passes all criteria,
    or None if it fails or data is unavailable.
    """
    try:
        t = yf.Ticker(symbol)
        info = t.info

        if not info or info.get("quoteType") not in ("EQUITY", "equity"):
            return None

        pe    = info.get("trailingPE")
        pb    = info.get("priceToBook")
        cr    = info.get("currentRatio")
        mcap  = info.get("marketCap")

        # Hard filter: skip if any required metric is missing
        if any(v is None for v in [pe, pb, cr]):
            return None

        # Apply criteria
        if pe  > MAX_PE:   return None
        if pb  > MAX_PB:   return None
        if cr  <= MIN_CURRENT: return None

        # 5-year average ROE (slower call)
        roe_5y = get_5y_avg_roe(t)
        if roe_5y is None or roe_5y <= MIN_ROE:
            return None

        return {
            "ticker":        symbol.replace(".L", ""),
            "yf_ticker":     symbol,
            "name":          info.get("longName") or info.get("shortName", symbol),
            "sector":        info.get("sector", "Unknown"),
            "market_cap":    mcap or 0,
            "pe_ratio":      round(pe, 2),
            "pb_ratio":      round(pb, 2),
            "current_ratio": round(cr, 2),
            "roe_5y_avg":    round(roe_5y, 2),
            "dividend_yield": round((info.get("dividendYield") or 0) * 100, 2),
            "currency":      info.get("currency", "GBP"),
        }

    except Exception as e:
        print(f"    Error processing {symbol}: {e}")
        return None


# ── Main scan ─────────────────────────────────────────────────────────────────
def run_scan():
    tickers = get_ftse_allshare_tickers()
    passed  = []
    total   = len(tickers)

    print(f"\nScanning {total} tickers (this will take a while)...\n")

    for i, symbol in enumerate(tickers, 1):
        print(f"[{i}/{total}] {symbol}", end=" ... ", flush=True)
        result = screen_ticker(symbol)
        if result:
            passed.append(result)
            print(f"✓ PASS  (PE={result['pe_ratio']}, PB={result['pb_ratio']}, "
                  f"CR={result['current_ratio']}, ROE={result['roe_5y_avg']}%)")
        else:
            print("✗")

        # Be polite to Yahoo Finance — avoid rate limiting
        time.sleep(0.5)

    # Sort by market cap descending
    passed.sort(key=lambda x: x["market_cap"], reverse=True)

    print(f"\n{'─'*50}")
    print(f"Scan complete. {len(passed)} stocks passed out of {total} scanned.")
    print(f"{'─'*50}\n")
    return passed


# ── Build and write output JSON ───────────────────────────────────────────────
def build_output(ftse_results):
    output = {
        "meta": {
            "last_updated":   datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "criteria": {
                "max_pe":           MAX_PE,
                "max_pb":           MAX_PB,
                "min_current_ratio": MIN_CURRENT,
                "min_roe_5y_avg":   MIN_ROE,
            },
            "counts": {
                "ftse":   len(ftse_results),
                "nyse":   0,
                "nasdaq": 0,
            }
        },
        "ftse":   ftse_results,
        "nyse":   [],   # placeholder for future expansion
        "nasdaq": [],   # placeholder for future expansion
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Output written to {OUTPUT_FILE}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ftse_results = run_scan()
    build_output(ftse_results)
