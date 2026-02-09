"""
Pre-processes the large NSE.json file to create instrument_master.json.
Uses underlying_symbol and asset_symbol for robust identification.
"""

import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import ijson
from decimal import Decimal
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths - Use relative paths for portability
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Try to find NSE.json in multiple locations
POSSIBLE_NSE_PATHS = [
    os.path.join(BASE_DIR, "NSE.json"),
    os.path.join(os.path.dirname(BASE_DIR), "bbt11", "NSE.json"),
    os.path.join(os.path.dirname(BASE_DIR), "NSE.json"),
]

NSE_JSON_PATH = next((p for p in POSSIBLE_NSE_PATHS if os.path.exists(p)), POSSIBLE_NSE_PATHS[1])
OUTPUT_PATH = os.path.join(BASE_DIR, "instrument_master.json")

# Key: App Ticker (yfinance)
# Value: Upstox underlying_symbol/asset_symbol
SYMBOL_MAP = {
    "^NSEI": "NIFTY",
    "^NSEBANK": "BANKNIFTY",
    "NIFTY_MIDCAP_100.NS": "MIDCPNIFTY",
    "RELIANCE.NS": "RELIANCE",
    "HDFCBANK.NS": "HDFCBANK",
    "INFY.NS": "INFY",
    "ITC.NS": "ITC",
    "TCS.NS": "TCS",
    "SBIN.NS": "SBIN",
    "ICICIBANK.NS": "ICICIBANK",
    "HINDUNILVR.NS": "HINDUNILVR",
    "BHARTIARTL.NS": "BHARTIARTL",
    "KOTAKBANK.NS": "KOTAKBANK",
    "ASIANPAINT.NS": "ASIANPAINT",
    "AXISBANK.NS": "AXISBANK",
    "MARUTI.NS": "MARUTI",
    "LT.NS": "LT",
    "BAJFINANCE.NS": "BAJFINANCE"
}

def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def preprocess_nse_data():
    instrument_master = {
        app_symbol: {"SPOT": None, "OPTIDX": [], "FUTIDX": [], "OPTSTK": [], "FUTSTK": []}
        for app_symbol in SYMBOL_MAP.keys()
    }

    # Reverse lookup map: Upstox symbol -> App symbol
    UPSTOX_TO_APP = {v: k for k, v in SYMBOL_MAP.items()}

    logger.info(f"Starting robust pre-processing of {NSE_JSON_PATH}")

    if not os.path.exists(NSE_JSON_PATH):
        logger.error(f"NSE.json not found at any of the tried paths: {POSSIBLE_NSE_PATHS}")
        return

    try:
        with open(NSE_JSON_PATH, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            count = 0
            for instrument in parser:
                count += 1
                if count % 50000 == 0:
                    logger.info(f"Processed {count} instruments...")

                segment = instrument.get('segment')
                us = instrument.get('underlying_symbol')
                asym = instrument.get('asset_symbol')
                ts = instrument.get('trading_symbol')
                
                # High-confidence matching
                app_symbol = UPSTOX_TO_APP.get(us) or UPSTOX_TO_APP.get(asym) or UPSTOX_TO_APP.get(ts)
                
                if app_symbol:
                    inst_type = instrument.get('instrument_type')
                    trading_symbol = ts
                    instrument_key = instrument.get('instrument_key')
                    
                    # 1. SPOT Instruments
                    if segment in ['NSE_INDEX', 'NSE_EQ'] and inst_type in ['INDEX', 'EQ']:
                        # Prefer primary entry (e.g. trading_symbol matches the key identifier)
                        target_sym = SYMBOL_MAP[app_symbol]
                        is_primary = (trading_symbol == target_sym)
                        
                        if is_primary or not instrument_master[app_symbol]["SPOT"]:
                            instrument_master[app_symbol]["SPOT"] = {
                                "instrument_key": instrument_key,
                                "name": instrument.get('name'),
                                "trading_symbol": trading_symbol
                            }
                    
                    # 2. F&O Instruments
                    elif segment == 'NSE_FO':
                        expiry_ts = instrument.get('expiry')
                        if not expiry_ts: continue
                        
                        expiry_date = datetime.fromtimestamp(expiry_ts / 1000).strftime('%Y-%m-%d')
                        is_index = (us or asym) in ['NIFTY', 'BANKNIFTY', 'MIDCPNIFTY']
                        
                        category = None
                        if inst_type == 'FUT':
                            category = "FUTIDX" if is_index else "FUTSTK"
                        elif inst_type in ['CE', 'PE']:
                            category = "OPTIDX" if is_index else "OPTSTK"
                        
                        if category:
                            data = {
                                "expiry": expiry_date,
                                "instrument_key": instrument_key,
                                "monthly": instrument.get('weekly') is False,
                                "weekly": instrument.get('weekly') is True,
                                "trading_symbol": trading_symbol
                            }
                            if inst_type in ['CE', 'PE']:
                                data["strike"] = float(instrument.get('strike_price', 0))
                                data["option_type"] = inst_type
                            
                            instrument_master[app_symbol][category].append(data)

        # Post-processing: Sorting
        final_master = {}
        for app_symbol, categories in instrument_master.items():
            if categories["SPOT"] or any(categories[k] for k in ["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"]):
                for k in ["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"]:
                    categories[k].sort(key=lambda x: (x['expiry'], x.get('strike', 0)))
                final_master[app_symbol] = categories

        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_master, f, indent=2)
        
        logger.info(f"Successfully created instrument master with {len(final_master)} assets at {OUTPUT_PATH}")

    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")

if __name__ == "__main__":
    preprocess_nse_data()
