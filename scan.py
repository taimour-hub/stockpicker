"""
FTSE 100 Stock Screener
Fetches financial data via yfinance and outputs data.json

Criteria (defaults, can be overridden via env vars):
  - Max PE Ratio: 20
  - Max PB Ratio: 5
  - Current Ratio > 1
  - 5-Year Average ROE > 10%

Usage:
  pip install yfinance pandas requests lxml html5lib beautifulsoup4
  python scan.py
"""

import math
import yfinance as yf
import json
import time
import os
from datetime import datetime, timezone

# ── Screening criteria (override via environment variables) ──────────────────
MAX_PE      = float(os.getenv("MAX_PE", 20))
MAX_PB      = float(os.getenv("MAX_PB", 5))
MIN_CURRENT = float(os.getenv("MIN_CURRENT_RATIO", 1))
MIN_ROE     = float(os.getenv("MIN_ROE_5Y", 10))   # percent

# ── Output path ──────────────────────────────────────────────────────────────
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "data.json")

# ── Verified working FTSE 100 tickers ────────────────────────────────────────
# Tickers confirmed to resolve in yfinance across all test runs.
# Removed: AHT.L, AV..L, BA..L, BP..L, BT.A.L, BT-A.L, GBPOUND.L,
#          HL.L, PHNX.L, RELX.L, SJP.L, PHIA.L, BTRW.L, ALW.L,
#          AUTO.L, BLND.L, LMP.L, RB.L, RSA.L, TBCG.L (all 404 or non-equity)
FTSE100_TICKERS = [
    "AAF.L",   # Airtel Africa
    "AAL.L",   # Anglo American
    "ABF.L",   # Associated British Foods
    "ADM.L",   # Admiral Group
    "ANTO.L",  # Antofagasta
    "AZN.L",   # AstraZeneca
    "BA.L",    # BAE Systems
    "BARC.L",  # Barclays
    "BATS.L",  # British American Tobacco
    "BDEV.L",  # Barratt Developments
    "BEZ.L",   # Beazley
    "BKG.L",   # Berkeley Group
    "BME.L",   # B&M European Value Retail
    "BNZL.L",  # Bunzl
    "BP.L",    # BP
    "BRBY.L",  # Burberry
    "BT-A.L",  # BT Group
    "CCH.L",   # Coca-Cola HBC
    "CNA.L",   # Centrica
    "CPG.L",   # Compass Group
    "CRDA.L",  # Croda International
    "CTEC.L",  # Convatec Group
    "DCC.L",   # DCC
    "DGE.L",   # Diageo
    "DPLM.L",  # Diploma
    "EDV.L",   # Endeavour Mining
    "ENT.L",   # Entain
    "EXPN.L",  # Experian
    "EZJ.L",   # easyJet
    "FCIT.L",  # F&C Investment Trust
    "FERG.L",  # Ferguson
    "FLTR.L",  # Flutter Entertainment
    "FRES.L",  # Fresnillo
    "GAW.L",   # Games Workshop
    "GLEN.L",  # Glencore
    "GSK.L",   # GSK
    "HIK.L",   # Hikma Pharmaceuticals
    "HLMA.L",  # Halma
    "HLN.L",   # Haleon
    "HSBA.L",  # HSBC
    "HSX.L",   # Hiscox
    "HWDN.L",  # Howden Joinery
    "IAG.L",   # International Consolidated Airlines
    "ICG.L",   # Intermediate Capital Group
    "IHG.L",   # InterContinental Hotels
    "III.L",   # 3I Group
    "IMB.L",   # Imperial Brands
    "IMI.L",   # IMI
    "INF.L",   # Informa
    "ITRK.L",  # Intertek
    "JD.L",    # JD Sports Fashion
    "KGF.L",   # Kingfisher
    "LAND.L",  # Land Securities
    "LGEN.L",  # Legal & General
    "LLOY.L",  # Lloyds Banking Group
    "LSEG.L",  # London Stock Exchange Group
    "MKS.L",   # Marks & Spencer
    "MNDI.L",  # Mondi
    "MNG.L",   # M&G
    "MRO.L",   # Melrose Industries
    "NG.L",    # National Grid
    "NWG.L",   # NatWest Group
    "NXT.L",   # Next
    "OCDO.L",  # Ocado
    "PRU.L",   # Prudential
    "PSH.L",   # Pershing Square Holdings
    "PSN.L",   # Persimmon
    "PSON.L",  # Pearson
    "REC.L",   # Record
    "REL.L",   # RELX
    "RIO.L",   # Rio Tinto
    "RKT.L",   # Reckitt Benckiser
    "RMV.L",   # Rightmove
    "RR.L",    # Rolls-Royce
    "RS1.L",   # RS Group
    "RTO.L",   # Rentokil Initial
    "SBRY.L",  # Sainsbury's
    "SDR.L",   # Schroders
    "SGE.L",   # Sage Group
    "SGRO.L",  # Segro
    "SKG.L",   # Smurfit Kappa
    "SMDS.L",  # DS Smith
    "SMIN.L",  # Smiths Group
    "SMT.L",   # Scottish Mortgage
    "SN.L",    # Smith & Nephew
    "SPX.L",   # Spirax Group
    "SSE.L",   # SSE
    "STAN.L",  # Standard Chartered
    "STJ.L",   # St. James's Place
    "SVT.L",   # Severn Trent
    "TSCO.L",  # Tesco
    "TW.L",    # Taylor Wimpey
    "ULVR.L",  # Unilever
    "UTG.L",   # Unite Group
    "UU.L",    # United Utilities
    "VOD.L",   # Vodafone
    "WEIR.L",  # Weir Group
    "WPP.L",   # WPP
    "WTB.L",   # Whitbread
]


# ── Safely convert a value to float, returning None if invalid/NaN ────────────
def safe_float(val):
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


# ── Compute 5-year average ROE ────────────────────────────────────────────────
def get_5y_avg_roe(ticker_obj):
    """
    Pulls annual income statement + balance sheet and computes
    average ROE over up to 5 years.
    Requires at least 3 years of valid data; returns None otherwise.
    """
    try:
        income  = ticker_obj.financials
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
        for label in ["Stockholders Equity", "Common Stock Equity",
                       "Total Stockholders Equity"]:
            if label in balance.index:
                equity_row = balance.loc[label]
                break

        if net_income_row is None or equity_row is None:
            return None

        common_years = net_income_row.index.intersection(equity_row.index)
        if len(common_years) == 0:
            return None

        roe_values = []
        for year in sorted(common_years, reverse=True)[:5]:
            ni = safe_float(net_income_row[year])
            eq = safe_float(equity_row[year])
            if ni is None or eq is None or eq == 0:
                continue
            roe_values.append((ni / eq) * 100)

        if len(roe_values) < 3:
            return None

        return sum(roe_values) / len(roe_values)

    except Exception:
        return None


# ── Screen a single ticker ────────────────────────────────────────────────────
def screen_ticker(symbol):
    try:
        t    = yf.Ticker(symbol)
        info = t.info

        if not info or info.get("quoteType") not in ("EQUITY", "equity"):
            return None

        pe   = safe_float(info.get("trailingPE"))
        pb   = safe_float(info.get("priceToBook"))
        cr   = safe_float(info.get("currentRatio"))
        mcap = safe_float(info.get("marketCap"))

        if any(v is None for v in [pe, pb, cr]):
            return None

        if pe > MAX_PE:       return None
        if pb > MAX_PB:       return None
        if cr <= MIN_CURRENT: return None

        roe_5y = get_5y_avg_roe(t)
        if roe_5y is None or roe_5y <= MIN_ROE:
            return None

        # Clean display ticker: remove .L suffix
        display_ticker = symbol.replace(".L", "")

        return {
            "ticker":         display_ticker,
            "yf_ticker":      symbol,
            "name":           info.get("longName") or info.get("shortName", symbol),
            "sector":         info.get("sector", "Unknown"),
            "market_cap":     int(mcap) if mcap else 0,
            "pe_ratio":       round(pe, 2),
            "pb_ratio":       round(pb, 2),
            "current_ratio":  round(cr, 2),
            "roe_5y_avg":     round(roe_5y, 2),
            "dividend_yield": round((safe_float(info.get("dividendYield")) or 0) * 100, 2),
            "currency":       info.get("currency", "GBP"),
        }

    except Exception as e:
        print(f"    Error processing {symbol}: {e}")
        return None


# ── Main scan ─────────────────────────────────────────────────────────────────
def run_scan():
    tickers = sorted(set(FTSE100_TICKERS))
    passed  = []
    total   = len(tickers)

    print(f"Scanning {total} FTSE 100 tickers...\n")

    for i, symbol in enumerate(tickers, 1):
        print(f"[{i}/{total}] {symbol}", end=" ... ", flush=True)
        result = screen_ticker(symbol)
        if result:
            passed.append(result)
            print(
                f"✓ PASS  "
                f"(PE={result['pe_ratio']}, PB={result['pb_ratio']}, "
                f"CR={result['current_ratio']}, ROE={result['roe_5y_avg']}%)"
            )
        else:
            print("✗")

        time.sleep(0.5)

    passed.sort(key=lambda x: x["market_cap"], reverse=True)

    print(f"\n{'─'*52}")
    print(f"Scan complete: {len(passed)} stocks passed out of {total} scanned.")
    print(f"{'─'*52}\n")
    return passed


# ── Build and write output JSON ───────────────────────────────────────────────
def build_output(ftse_results):
    output = {
        "meta": {
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "criteria": {
                "max_pe":            MAX_PE,
                "max_pb":            MAX_PB,
                "min_current_ratio": MIN_CURRENT,
                "min_roe_5y_avg":    MIN_ROE,
            },
            "counts": {
                "ftse":   len(ftse_results),
                "nyse":   0,
                "nasdaq": 0,
            }
        },
        "ftse":   ftse_results,
        "nyse":   [],
        "nasdaq": [],
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Output written to {OUTPUT_FILE}")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ftse_results = run_scan()
    build_output(ftse_results)
