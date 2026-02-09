"""
Upstox F&O Complete - CORRECT API Structure
✅ Uses REAL Upstox response structure (not assumed)
✅ Both Options AND Futures data
✅ Greeks extraction (delta, gamma, vega, theta, IV)
✅ Advanced insights from Greeks
"""

import requests
import json
import os
import webbrowser
import pandas as pd
import numpy as np
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
import time
from calendar import monthrange

logger = logging.getLogger(__name__)

# Load the pre-processed instrument master data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTRUMENT_MASTER_PATH = os.path.join(BASE_DIR, "instrument_master.json")
INSTRUMENT_MASTER: Dict[str, Any] = {}
if os.path.exists(INSTRUMENT_MASTER_PATH):
    try:
        with open(INSTRUMENT_MASTER_PATH, 'r', encoding='utf-8') as f:
            INSTRUMENT_MASTER = json.load(f)
        logger.info(f"Successfully loaded instrument master from {INSTRUMENT_MASTER_PATH}")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {INSTRUMENT_MASTER_PATH}. File might be corrupted.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading {INSTRUMENT_MASTER_PATH}: {e}")
else:
    logger.warning(f"Instrument master file not found at {INSTRUMENT_MASTER_PATH}. F&O functionality might be limited. Please run preprocess_nse_data.py.")


def _get_instrument_key(
    symbol: str,
    instrument_type: str, # e.g., "SPOT", "OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"
    expiry_date: Optional[str] = None,
    strike_price: Optional[float] = None,
    option_type: Optional[str] = None # "CE" or "PE"
) -> Optional[str]:
    """
    Retrieves the Upstox instrument_key from INSTRUMENT_MASTER.
    """
    if not INSTRUMENT_MASTER:
        logger.warning("INSTRUMENT_MASTER is empty. Cannot retrieve instrument key.")
        return None

    # Normalization for matching instrument_master.json keys
    normalized_symbol = symbol
    if normalized_symbol == "Nifty 50":
        normalized_symbol = "^NSEI"
    elif normalized_symbol == "Bank Nifty":
        normalized_symbol = "^NSEBANK"
    elif normalized_symbol == "Nifty Midcap 100":
        normalized_symbol = "NIFTY_MIDCAP_100.NS"
    elif not normalized_symbol.startswith("^") and not normalized_symbol.endswith(".NS"):
        normalized_symbol = f"{normalized_symbol}.NS"
    
    if normalized_symbol not in INSTRUMENT_MASTER:
        # Fallback: check if the original symbol is used as key
        if symbol in INSTRUMENT_MASTER:
             normalized_symbol = symbol
        else:
            logger.warning(f"Normalized symbol {normalized_symbol} (original: {symbol}) not found in INSTRUMENT_MASTER.")
            return None
        
    symbol_data = INSTRUMENT_MASTER[normalized_symbol]
    
    if instrument_type == "SPOT":
        spot_data = symbol_data.get("SPOT")
        if isinstance(spot_data, dict):
            return spot_data.get("instrument_key")
        return None
    
    if instrument_type in ["OPTIDX", "OPTSTK"] and expiry_date and strike_price and option_type:
        options = symbol_data.get(instrument_type, [])
        for opt in options:
            if opt.get("expiry") == expiry_date and \
               opt.get("strike") == strike_price and \
               opt.get("option_type") == option_type:
                return opt.get("instrument_key")
    
    if instrument_type in ["FUTIDX", "FUTSTK"] and expiry_date:
        futures = symbol_data.get(instrument_type, [])
        for fut in futures:
            if fut.get("expiry") == expiry_date:
                return fut.get("instrument_key")

    logger.warning(f"Instrument key not found for {normalized_symbol}, type {instrument_type}, expiry {expiry_date}, strike {strike_price}, opt_type {option_type}")
    return None

class UpstoxAuth:
    """Simplified OAuth - 24 hour tokens"""
    
    def __init__(self, api_key: str, api_secret: str, redirect_uri: str = "http://localhost:5600"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.token_file = "upstox_tokens.json"
    
    class OAuthHandler(BaseHTTPRequestHandler):
        auth_code = None
        
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            UpstoxAuth.OAuthHandler.auth_code = query.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization successful! Close this tab.")
        
        def log_message(self, format, *args):
            pass
    
    def get_auth_code(self):
        auth_url = (
            "https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code&client_id={self.api_key}"
            f"&redirect_uri={self.redirect_uri}"
        )
        
        server = HTTPServer(("localhost", 5600), self.OAuthHandler)
        print("Opening browser for Upstox login...") # Removed emoji to prevent crash
        webbrowser.open(auth_url)
        server.handle_request()
        
        return self.OAuthHandler.auth_code
    
    def exchange_code_for_tokens(self, code: str) -> Dict:
        url = "https://api.upstox.com/v2/login/authorization/token"
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": self.redirect_uri
        }
        
        response = requests.post(url, data=payload)
        data = response.json()
        
        if "access_token" not in data:
            raise RuntimeError(f"Token exchange failed: {data}")
        
        data["timestamp"] = time.time()
        data["expires_at"] = time.time() + (24 * 3600)
        
        with open(self.token_file, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info("✓ Token saved (valid 24 hours)")
        return data
    
    def get_access_token(self) -> str:
        if not os.path.exists(self.token_file):
            code = self.get_auth_code()
            if not code:
                raise RuntimeError("Authorization failed")
            tokens = self.exchange_code_for_tokens(code)
            return tokens["access_token"]
        
        with open(self.token_file, "r") as f:
            tokens = json.load(f)
        
        if time.time() > tokens.get("expires_at", 0):
            logger.warning("Token expired, re-authorizing...")
            os.remove(self.token_file)
            return self.get_access_token()
        
        return tokens["access_token"]

    def invalidate_token(self):
        """Force invalidate local token"""
        if os.path.exists(self.token_file):
            try:
                os.remove(self.token_file)
                logger.info("Token file removed (invalidated).")
            except Exception as e:
                logger.error(f"Failed to remove token file: {e}")


class UpstoxFOData:
    """Fetch Options AND Futures with correct structure"""
    
    def __init__(self, auth: UpstoxAuth):
        self.auth = auth
        self.base_url = "https://api.upstox.com/v2"
        self.last_response: Optional[Dict] = None # Store last response for analysis
        self.key_map: Dict[str, str] = {} # Map requested keys to successful response keys
    
    def get_headers(self) -> Dict:
        access_token = self.auth.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
    
    def _make_api_call(self, url: str, params: Dict) -> Dict:
        """Helper to make API call with automatic token refresh on invalid token error"""
        headers = self.get_headers()
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            self.last_response = data # Store for debugging/analysis
            
            # Check for token invalid error (UDAPI100050)
            if data.get("status") == "error":
                errors = data.get("errors", [])
                if errors and errors[0].get("errorCode") == "UDAPI100050":
                    logger.warning("Token invalid (UDAPI100050). Invalidating and retrying...")
                    self.auth.invalidate_token()
                    
                    # Retry once with new token (get_headers triggers auth flow)
                    headers = self.get_headers() 
                    response = requests.get(url, headers=headers, params=params)
                    data = response.json()
                    self.last_response = data
            
            return data
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise

    def get_spot_price(self, symbol: str) -> Optional[float]:
        """Get real-time spot price"""
        
        instrument_key = _get_instrument_key(symbol, "SPOT") # Use helper
        
        # Check if we already have a mapped key for this original instrument_key
        if instrument_key in self.key_map:
            instrument_key = self.key_map[instrument_key]

        # If helper fails, provide robust fallbacks
        if not instrument_key:
            if symbol == "Nifty 50" or symbol == "^NSEI":
                instrument_key = "NSE_INDEX|Nifty 50"
            elif symbol == "Bank Nifty" or symbol == "^NSEBANK":
                instrument_key = "NSE_INDEX|Nifty Bank"
            elif symbol == "Nifty Midcap 100" or "MIDCAP" in symbol.upper():
                 instrument_key = "NSE_INDEX|Nifty Midcap 100"
            elif not symbol.startswith("^"):
                 instrument_key = f"NSE_EQ|{symbol}"
        
        if not instrument_key:
            logger.warning(f"Could not get SPOT instrument key for {symbol}")
            return None
        
        try:
            url = f"{self.base_url}/market-quote/quotes"
            params = {"instrument_key": instrument_key}
            
            data = self._make_api_call(url, params)
            
            if data.get("status") == "success":
                # Check for direct match or variants
                keys_to_check = [instrument_key, instrument_key.replace("|", ":"), instrument_key.replace(":", "|")]
                
                found_key = None
                for k in keys_to_check:
                    if k in data["data"]:
                        found_key = k
                        break
                
                if found_key:
                    # Update key map if it was a variant
                    if found_key != instrument_key:
                        self.key_map[params["instrument_key"]] = found_key
                    
                    ltp = data["data"][found_key]["last_price"]
                    logger.info(f"Spot price for {symbol}: {ltp}")
                    return float(ltp)
                else:
                    # Fallback: Scan all returned keys
                    for key, details in data.get("data", {}).items():
                        if "last_price" in details:
                            # Map this successful key for future use
                            self.key_map[params["instrument_key"]] = key
                            ltp = details["last_price"]
                            logger.info(f"Spot price for {symbol}: {ltp} (via discovered key {key})")
                            return float(ltp)
                    
                    logger.error(f"Spot price API failed or key missing. Status: {data.get('status')}, Key: {instrument_key}, Response Keys: {list(data.get('data', {}).keys())}")
            else:
                logger.error(f"Spot price API returned error status: {data}")

        except Exception as e:
            logger.warning(f"Spot price fetch failed for {symbol}: {e}")
        
        return None
    
    def get_spot_quote(self, symbol: str) -> Dict:
        """Get full spot quote (LTP, OHLC, Change)"""
        
        instrument_key = _get_instrument_key(symbol, "SPOT") # Use helper
        
        # Check if we already have a mapped key for this original instrument_key
        if instrument_key in self.key_map:
            instrument_key = self.key_map[instrument_key]

        # If helper fails, provide robust fallbacks
        if not instrument_key:
            if symbol == "Nifty 50" or symbol == "^NSEI":
                instrument_key = "NSE_INDEX|Nifty 50"
            elif symbol == "Bank Nifty" or symbol == "^NSEBANK":
                instrument_key = "NSE_INDEX|Nifty Bank"
            elif symbol == "Nifty Midcap 100" or "MIDCAP" in symbol.upper():
                 instrument_key = "NSE_INDEX|Nifty Midcap 100"
            elif symbol == "Nifty Smallcap 100" or "SMALLCAP" in symbol.upper():
                 # Try 100 first, common benchmark
                 instrument_key = "NSE_INDEX|Nifty Smallcap 100" 
            elif not symbol.startswith("^"):
                 instrument_key = f"NSE_EQ|{symbol}"
        
        if not instrument_key:
            logger.warning(f"Could not get SPOT instrument key for {symbol}")
            return {}
        
        if not instrument_key:
            logger.warning(f"Could not get SPOT instrument key for {symbol}")
            return {}
            
        # Candidate keys to try (handle case sensitivity & variants)
        candidate_keys = [instrument_key]
        
        # Specific fallbacks for Indices
        if "SMALLCAP" in symbol.upper():
            candidate_keys.extend([
                "NSE_INDEX|Nifty Smallcap 100",
                "NSE_INDEX|NIFTY SMALLCAP 100", 
                "NSE_INDEX|Nifty Smallcap 250",
                "NSE_INDEX|NIFTY SMLCAP 100"
            ])
        elif "MIDCAP" in symbol.upper():
            candidate_keys.extend([
                "NSE_INDEX|Nifty Midcap 100",
                "NSE_INDEX|NIFTY MIDCAP 100",
                "NSE_INDEX|Nifty Midcap 150"
            ])
            
        for key in candidate_keys:
            try:
                url = f"{self.base_url}/market-quote/quotes"
                params = {"instrument_key": key}
                
                data = self._make_api_call(url, params)
                
                if data.get("status") == "success":
                    # Check for direct match or variants
                    found_key = None
                    # The response key matches the requested key (usually)
                    # or it might be colon separated
                    keys_to_check = [key, key.replace("|", ":"), key.replace(":", "|")]
                    
                    for k in keys_to_check:
                        if k in data.get("data", {}):
                            found_key = k
                            break
                    
                    # Fallback scan if explicit key not found
                    if not found_key:
                        for k in data.get("data", {}):
                             found_key = k
                             break
                    
                    if found_key:
                        quote = data["data"][found_key]
                        ltp = quote.get("last_price")
                        ohlc = quote.get("ohlc", {})
                        prev_close = ohlc.get("close")
                        
                        change = 0.0
                        change_pct = 0.0
                        
                        if ltp and prev_close:
                            change = ltp - prev_close
                            change_pct = (change / prev_close) * 100
                        
                        # Cache this working key for future
                        if key != instrument_key:
                            self.key_map[instrument_key] = key
                        
                        return {
                            "symbol": symbol,
                            "ltp": ltp,
                            "previous_close": prev_close,
                            "change": change,
                            "change_pct": change_pct,
                            "open": ohlc.get("open"),
                            "high": ohlc.get("high"),
                            "low": ohlc.get("low")
                        }
            except Exception as e:
                logger.warning(f"Failed to fetch quote for {symbol} with key {key}: {e}")
                continue

        logger.warning(f"Quote fetch failed for {symbol} after trying keys: {candidate_keys}")
        return {}

    def get_holdings(self) -> List[Dict]:
        """Fetch long-term holdings"""
        try:
            url = f"{self.base_url}/portfolio/long-term-holdings"
            data = self._make_api_call(url, {})
            
            if data.get("status") == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Holdings fetch failed: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """Fetch short-term positions"""
        try:
            url = f"{self.base_url}/portfolio/short-term-positions"
            data = self._make_api_call(url, {})
            
            if data.get("status") == "success":
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Positions fetch failed: {e}")
            return []

    def get_option_chain(
        self,
        symbol: str = "Nifty 50",
        expiry_date: Optional[str] = None,
        max_distance_pct: float = 12.0,
        expiry_type: str = "weekly" # Added parameter for weekly/monthly
    ) -> Tuple[pd.DataFrame, float]:
        """
        Get option chain with CORRECT Upstox structure
        """
        url = f"{self.base_url}/option/chain"
        
        if not expiry_date:
            expiry_date = self._get_next_expiry(symbol, "options", expiry_type) # Use new expiry logic

        # For option chain endpoint, it's typically an underlying + expiry.
        if symbol == "Nifty 50":
            chain_instrument_key = "NSE_INDEX|Nifty 50"
        elif symbol == "Bank Nifty":
            chain_instrument_key = "NSE_INDEX|Nifty Bank"
        else:
            # Look up the SPOT instrument key for the stock
            chain_instrument_key = _get_instrument_key(symbol, "SPOT")
            
            # Use mapped key if available (e.g. ISIN -> Symbol)
            if chain_instrument_key and chain_instrument_key in self.key_map:
                 chain_instrument_key = self.key_map[chain_instrument_key]

            if not chain_instrument_key:
                 # Fallback to simple construction if lookup fails (might work if pattern matches)
                 chain_instrument_key = f"NSE_EQ|{symbol}"

        params = {
            "instrument_key": chain_instrument_key,
            "expiry_date": expiry_date
        }
        
        logger.info(f"Fetching option chain: {symbol} expiry {expiry_date}")
        
        data = self._make_api_call(url, params)
        
        # DEBUG LOGGING FOR ANALYSIS
        # logger.info(f"Option Chain Response for {symbol}: {json.dumps(data, indent=2) if data else 'None'}")
        
        if data.get("status") != "success":
            # Try fallback key for stocks if first attempt failed
            if "NSE_EQ" in chain_instrument_key and "|" in chain_instrument_key:
                 # Try colon
                 params["instrument_key"] = chain_instrument_key.replace("|", ":")
                 logger.info(f"Retrying option chain with key: {params['instrument_key']}")
                 data = self._make_api_call(url, params)
            
            # If still failed, try simple symbol format for stocks
            if data.get("status") != "success" and symbol not in ["Nifty 50", "Bank Nifty"]:
                 params["instrument_key"] = f"NSE_EQ|{symbol}"
                 logger.info(f"Retrying option chain with fallback key: {params['instrument_key']}")
                 data = self._make_api_call(url, params)

            if data.get("status") != "success":     
                raise RuntimeError(f"Option chain failed: {data}")
        
        spot_price = self.get_spot_price(symbol)
        if spot_price is None:
             raise RuntimeError(f"Could not get spot price for {symbol} for option chain analysis.")
             
        rows = []
        if "data" in data and data["data"]:
            for item in data["data"]:
                strike_price = item.get("strike_price")
                if strike_price is None:
                    continue
                
                call_data = item.get("call_options", {})
                call_market = call_data.get("market_data", {})
                call_greeks = call_data.get("option_greeks", {})
                
                put_data = item.get("put_options", {})
                put_market = put_data.get("market_data", {})
                put_greeks = put_data.get("option_greeks", {})
                
                row = {
                    "strike": strike_price,
                    "CE_LTP": call_market.get("ltp"),
                    "CE_Volume": call_market.get("volume", 0),
                    "CE_OI": call_market.get("oi", 0),
                    "CE_OI_Prev": call_market.get("prev_oi", 0),
                    "CE_Bid": call_market.get("bid_price"),
                    "CE_Ask": call_market.get("ask_price"),
                    "CE_IV": call_greeks.get("iv"),
                    "CE_Delta": call_greeks.get("delta"),
                    "CE_Gamma": call_greeks.get("gamma"),
                    "CE_Theta": call_greeks.get("theta"),
                    "CE_Vega": call_greeks.get("vega"),
                    "PE_LTP": put_market.get("ltp"),
                    "PE_Volume": put_market.get("volume", 0),
                    "PE_OI": put_market.get("oi", 0),
                    "PE_OI_Prev": put_market.get("prev_oi", 0),
                    "PE_Bid": put_market.get("bid_price"),
                    "PE_Ask": put_market.get("ask_price"),
                    "PE_IV": put_greeks.get("iv"),
                    "PE_Delta": put_greeks.get("delta"),
                    "PE_Gamma": put_greeks.get("gamma"),
                    "PE_Theta": put_greeks.get("theta"),
                    "PE_Vega": put_greeks.get("vega"),
                }
                row["CE_OI_Change"] = row["CE_OI"] - row["CE_OI_Prev"] if row["CE_OI"] and row["CE_OI_Prev"] else 0
                row["PE_OI_Change"] = row["PE_OI"] - row["PE_OI_Prev"] if row["PE_OI"] and row["PE_OI_Prev"] else 0
                
                rows.append(row)
        else:
            logger.warning(f"No data field in response or empty data for {symbol}")
        
        if not rows:
            logger.warning(f"No option chain data found for {symbol} (rows empty). Response status: {data.get('status')}")
            return pd.DataFrame(), spot_price

        df = pd.DataFrame(rows).sort_values("strike").reset_index(drop=True)
        
        df_filtered = self._filter_liquid_strikes(df, spot_price, max_distance_pct)
        return df_filtered, spot_price
    
    def get_futures_data(
        self,
        symbol: str,
        expiry_date: Optional[str] = None,
        expiry_type: str = "monthly" # Added parameter
    ) -> Dict:
        """
        Get futures data for premium/discount analysis
        """
        if not expiry_date:
            expiry_date = self._get_next_expiry(symbol, "futures", expiry_type) # Use new expiry logic
        
        instrument_type = "FUTIDX" if "Nifty" in symbol or "Bank Nifty" in symbol else "FUTSTK"
        instrument_key = _get_instrument_key(symbol, instrument_type, expiry_date) # Use helper
        
        keys_to_try = []
        if instrument_key:
            keys_to_try.append(instrument_key)
            keys_to_try.append(instrument_key.replace("|", ":"))
        
        # Fallback keys
        try:
            exp_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
            yy = exp_dt.strftime("%y")
            mon = exp_dt.strftime("%b").upper()
            
            fut_sym = symbol
            if symbol == "Nifty 50": fut_sym = "NIFTY"
            elif symbol == "Bank Nifty": fut_sym = "BANKNIFTY"
            
            keys_to_try.append(f"NSE_FO|{fut_sym}{yy}{mon}FUT")
            keys_to_try.append(f"NSE_FO:{fut_sym}{yy}{mon}FUT")
        except:
            pass
            
        if not keys_to_try:
             return {"futures_price": None, "interpretation": "Futures data unavailable (no keys to try)"}

        for key in keys_to_try:
            try:
                url = f"{self.base_url}/market-quote/quotes"
                params = {"instrument_key": key}
                
                data = self._make_api_call(url, params)
                
                # DEBUG: Log futures response
                # logger.info(f"Futures Response for {key}: {json.dumps(data, indent=2)}")
                
                if data.get("status") == "success":
                    # Check if any key in data matches the requested key or its variants
                    found_key = None
                    if key in data.get("data", {}):
                        found_key = key
                    elif key.replace("|", ":") in data.get("data", {}):
                        found_key = key.replace("|", ":")
                    else:
                        # Fallback: scan all keys in response
                        for k in data.get("data", {}):
                            found_key = k
                            break
                    
                    if found_key:
                        futures_data = data["data"][found_key]
                        
                        futures_ltp = futures_data.get("last_price")
                        futures_oi = futures_data.get("oi")
                        futures_volume = futures_data.get("volume")
                        
                        spot_price = self.get_spot_price(symbol)
                        
                        if futures_ltp and spot_price:
                            basis = futures_ltp - spot_price
                            basis_pct = (basis / spot_price) * 100
                            
                            # Estimate days to expiry
                            try:
                                exp_dt_obj = datetime.strptime(expiry_date, "%Y-%m-%d")
                                days_to_expiry = (exp_dt_obj - datetime.now()).days
                                if days_to_expiry <= 0: days_to_expiry = 1
                            except:
                                days_to_expiry = 30
                            
                            annual_carry = basis_pct * (365 / days_to_expiry)
                            
                            return {
                                "futures_price": futures_ltp,
                                "spot_price": spot_price,
                                "basis": basis,
                                "basis_pct": basis_pct,
                                "annual_carry": annual_carry,
                                "futures_oi": futures_oi,
                                "futures_volume": futures_volume,
                                "interpretation": self._interpret_basis(basis_pct)
                            }
                        
            # If loop finishes without return, try next key
            except Exception as e:
                logger.warning(f"Futures fetch failed for {symbol} with key {key}: {e}")
        
        return {
            "futures_price": None,
            "interpretation": "Futures data unavailable"
        }
    
    def _interpret_basis(self, basis_pct: float) -> str:
        """Interpret futures basis"""
        if basis_pct > 0.5:
            return f"Premium {basis_pct:.2f}% - Strong bullish sentiment"
        elif basis_pct > 0.2:
            return f"Premium {basis_pct:.2f}% - Mild bullish sentiment"
        elif basis_pct < -0.2:
            return f"Discount {abs(basis_pct):.2f}% - Bearish sentiment"
        else:
            return "Fair pricing - Neutral sentiment"
    
    def calculate_greeks_analysis(self, option_chain: pd.DataFrame, spot_price: float) -> Dict:
        """
        Advanced Greeks analysis
        
        Insights:
        - Gamma exposure (where MMs hedge most)
        - Vanna (IV-spot sensitivity)
        - Total delta (directional bias)
        - Theta decay (time value)
        """
        # Find ATM
        atm_idx = (option_chain["strike"] - spot_price).abs().idxmin()
        atm_data = option_chain.iloc[atm_idx]
        
        # Total delta (net directional exposure)
        # Calls positive delta, puts negative delta
        total_call_delta = (option_chain["CE_Delta"].fillna(0) * option_chain["CE_OI"]).sum()
        total_put_delta = (option_chain["PE_Delta"].fillna(0) * option_chain["PE_OI"]).sum()
        net_delta = total_call_delta + total_put_delta  # Put delta is negative
        
        # Gamma exposure (max gamma = where MMs hedge most)
        option_chain["total_gamma"] = (
            option_chain["CE_Gamma"].fillna(0) * option_chain["CE_OI"] +
            option_chain["PE_Gamma"].fillna(0) * option_chain["PE_OI"]
        )
        max_gamma_idx = option_chain["total_gamma"].idxmax()
        max_gamma_strike = option_chain.loc[max_gamma_idx, "strike"]
        
        # Total theta (time decay per day)
        total_theta = (
            (option_chain["CE_Theta"].fillna(0) * option_chain["CE_OI"]).sum() +
            (option_chain["PE_Theta"].fillna(0) * option_chain["PE_OI"]).sum()
        )
        
        # Vega (IV sensitivity)
        total_vega = (
            (option_chain["CE_Vega"].fillna(0) * option_chain["CE_OI"]).sum() +
            (option_chain["PE_Vega"].fillna(0) * option_chain["PE_OI"]).sum()
        )
        
        # Interpret delta
        if net_delta > 0:
            delta_interpretation = f"Net LONG bias (delta: {net_delta:.0f})"
        elif net_delta < 0:
            delta_interpretation = f"Net SHORT bias (delta: {net_delta:.0f})"
        else:
            delta_interpretation = "Delta neutral"
        
        return {
            "net_delta": net_delta,
            "delta_interpretation": delta_interpretation,
            "max_gamma_strike": max_gamma_strike,
            "gamma_interpretation": f"Max hedging at ₹{max_gamma_strike:.0f}",
            "total_theta": total_theta,
            "theta_interpretation": f"₹{abs(total_theta):,.0f} time decay/day",
            "total_vega": total_vega,
            "vega_interpretation": f"₹{abs(total_vega):,.0f} exposure per 1% IV change",
            "atm_call_iv": atm_data.get("CE_IV"),
            "atm_put_iv": atm_data.get("PE_IV")
        }
    
    def _filter_liquid_strikes(
        self,
        option_chain: pd.DataFrame,
        spot_price: float,
        max_distance_pct: float
    ) -> pd.DataFrame:
        """Filter to liquid strikes"""
        option_chain = option_chain.copy()
        option_chain["distance_pct"] = abs((option_chain["strike"] - spot_price) / spot_price) * 100
        
        filtered = option_chain[option_chain["distance_pct"] <= max_distance_pct].copy()
        
        # Liquidity filter
        filtered["has_liquidity"] = (
            (filtered["CE_OI"] + filtered["PE_OI"] > 100) |
            (filtered["CE_Volume"] + filtered["PE_Volume"] > 10) |
            (filtered["CE_IV"].notna()) |
            (filtered["PE_IV"].notna())
        )
        
        filtered = filtered[filtered["has_liquidity"]].copy()
        filtered = filtered.drop(["distance_pct", "has_liquidity"], axis=1)
        
        logger.info(f"✓ Filtered to {len(filtered)} liquid strikes")
        
        return filtered.reset_index(drop=True)
    
    def _filter_by_atm(self, option_chain: pd.DataFrame, max_distance_pct: float) -> pd.DataFrame:
        """Filter when no spot price (use OI)"""
        option_chain = option_chain.copy()
        option_chain["total_oi"] = option_chain["CE_OI"] + option_chain["PE_OI"]
        atm_idx = option_chain["total_oi"].idxmax()
        atm_strike = option_chain.loc[atm_idx, "strike"]
        
        option_chain["distance_pct"] = abs((option_chain["strike"] - atm_strike) / atm_strike) * 100
        filtered = option_chain[option_chain["distance_pct"] <= max_distance_pct].copy()
        filtered = filtered.drop(["total_oi", "distance_pct"], axis=1)
        
        return filtered.reset_index(drop=True)
    
    def calculate_pcr(self, option_chain: pd.DataFrame) -> Dict:
        """PCR analysis"""
        total_call_oi = option_chain["CE_OI"].sum()
        total_put_oi = option_chain["PE_OI"].sum()
        total_call_vol = option_chain["CE_Volume"].sum()
        total_put_vol = option_chain["PE_Volume"].sum()
        
        pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        pcr_vol = total_put_vol / total_call_vol if total_call_vol > 0 else 0
        
        if pcr_oi > 1.4:
            sentiment = "OVERSOLD"
            interpretation = "Excessive put buildup - potential bounce"
        elif pcr_oi < 0.6:
            sentiment = "OVERBOUGHT"
            interpretation = "Excessive call buildup - potential correction"
        else:
            sentiment = "NEUTRAL"
            interpretation = "Balanced options activity"
        
        return {
            "pcr_oi": pcr_oi,
            "pcr_volume": pcr_vol,
            "total_call_oi": int(total_call_oi),
            "total_put_oi": int(total_put_oi),
            "sentiment": sentiment,
            "interpretation": interpretation
        }
    
    def calculate_max_pain(self, option_chain: pd.DataFrame, current_price: float) -> Dict:
        """Max Pain calculation"""
        strikes = option_chain["strike"].values
        max_pain_values = []
        
        for strike in strikes:
            below = option_chain[option_chain["strike"] < strike]
            call_pain = (below["CE_OI"] * (strike - below["strike"])).sum()
            
            above = option_chain[option_chain["strike"] > strike]
            put_pain = (above["PE_OI"] * (above["strike"] - strike)).sum()
            
            max_pain_values.append(call_pain + put_pain)
        
        min_idx = np.argmin(max_pain_values)
        max_pain_strike = strikes[min_idx]
        
        distance = ((max_pain_strike - current_price) / current_price) * 100
        
        return {
            "max_pain_strike": float(max_pain_strike),
            "distance_pct": distance,
            "interpretation": f"₹{max_pain_strike:.0f} ({distance:+.1f}% from spot)"
        }
    
    def get_oi_analysis(self, option_chain: pd.DataFrame) -> Dict:
        """OI support/resistance"""
        max_call_strike = option_chain.loc[option_chain["CE_OI"].idxmax(), "strike"]
        max_put_strike = option_chain.loc[option_chain["PE_OI"].idxmax(), "strike"]
        
        call_buildup = option_chain[option_chain["CE_OI_Change"] > 0].nlargest(5, "CE_OI_Change")
        put_buildup = option_chain[option_chain["PE_OI_Change"] > 0].nlargest(5, "PE_OI_Change")
        
        return {
            "call_resistance": float(max_call_strike),
            "put_support": float(max_put_strike),
            "call_buildups": call_buildup["strike"].tolist(),
            "put_buildups": put_buildup["strike"].tolist()
        }
    
    def _get_next_expiry(self, symbol: str, instrument_category: str = "options", expiry_type: str = "weekly") -> str:
        """
        Determines the next appropriate expiry date based on symbol and desired expiry type (weekly/monthly).
        This assumes INSTRUMENT_MASTER is populated with expiry dates for different instruments.
        """
        today = datetime.now()
        
        # Consistent normalization
        normalized_symbol = symbol
        if normalized_symbol == "Nifty 50":
            normalized_symbol = "^NSEI"
        elif normalized_symbol == "Bank Nifty":
            normalized_symbol = "^NSEBANK"
        elif normalized_symbol == "Nifty Midcap 100":
            normalized_symbol = "NIFTY_MIDCAP_100.NS"
        elif not normalized_symbol.startswith("^") and not normalized_symbol.endswith(".NS"):
            normalized_symbol = f"{normalized_symbol}.NS"

        if normalized_symbol not in INSTRUMENT_MASTER or not INSTRUMENT_MASTER[normalized_symbol]:
            logger.warning(f"Normalized symbol {normalized_symbol} (original: {symbol}) not found in INSTRUMENT_MASTER. Cannot determine expiry.")
            return self._get_fallback_expiry(symbol)

        symbol_data = INSTRUMENT_MASTER[normalized_symbol]
        
        instrument_list_key = None
        if instrument_category == "options":
            instrument_list_key = "OPTIDX" if "Nifty" in symbol or "Bank Nifty" in symbol else "OPTSTK"
        elif instrument_category == "futures":
            instrument_list_key = "FUTIDX" if "Nifty" in symbol or "Bank Nifty" in symbol else "FUTSTK"
        
        if not instrument_list_key or instrument_list_key not in symbol_data:
            logger.warning(f"No {instrument_category} data for {normalized_symbol} in INSTRUMENT_MASTER. Falling back.")
            return self._get_fallback_expiry(symbol)

        instrument_list = symbol_data[instrument_list_key]
            
        available_expiries_dt = sorted(list(set([
            datetime.strptime(item["expiry"], "%Y-%m-%d") for item in instrument_list 
            if "expiry" in item and datetime.strptime(item["expiry"], "%Y-%m-%d").date() >= today.date()
        ])))

        if not available_expiries_dt:
            logger.warning(f"No upcoming expiries found for {symbol} in INSTRUMENT_MASTER. Falling back.")
            return self._get_fallback_expiry(symbol)

        filtered_expiries_str = []
        for exp_dt in available_expiries_dt:
            exp_str = exp_dt.strftime("%Y-%m-%d")
            
            # Check if this expiry is marked as weekly or monthly in INSTRUMENT_MASTER
            # This requires a more complex check as the list might contain mixed types
            is_weekly = any(item.get("expiry") == exp_str and item.get("weekly", False) for item in instrument_list)
            is_monthly = any(item.get("expiry") == exp_str and item.get("monthly", False) for item in instrument_list)
            
            if expiry_type == "weekly" and is_weekly:
                # For weekly, ensure it's not a monthly expiry day itself
                if not (exp_dt.day > 20 and exp_dt.weekday() == 3 and instrument_category == "futures"): # Heuristic for monthly futures
                     filtered_expiries_str.append(exp_str)
            elif expiry_type == "monthly" and is_monthly:
                filtered_expiries_str.append(exp_str)
            elif expiry_type not in ["weekly", "monthly"]: # If not specified, take the closest
                 filtered_expiries_str.append(exp_str)

        if filtered_expiries_str:
            # Select the closest expiry
            return filtered_expiries_str[0]
        
        # If weekly requested but not found, try finding ANY valid expiry (likely monthly) from Master
        # This handles cases where stocks don't have weekly expiries
        if expiry_type == "weekly":
             all_expiries = sorted(list(set([
                item["expiry"] for item in instrument_list 
                if "expiry" in item and datetime.strptime(item["expiry"], "%Y-%m-%d").date() >= today.date()
             ])))
             if all_expiries:
                 exp_dates = [datetime.strptime(e, "%Y-%m-%d") for e in all_expiries]
                 exp_dates.sort()
                 next_exp = exp_dates[0].strftime("%Y-%m-%d")
                 logger.info(f"No weekly expiry for {symbol}, switching to next available: {next_exp}")
                 return next_exp

        logger.warning(f"No {expiry_type} expiries found for {symbol} in INSTRUMENT_MASTER. Falling back.")
        return self._get_fallback_expiry(symbol)

    def _get_fallback_expiry(self, symbol: str) -> str:
        """Original expiry logic as fallback if INSTRUMENT_MASTER lookup fails or yields no suitable expiry."""
        today = datetime.now()
        
        if "Nifty" in symbol or "Bank Nifty" in symbol: # Indices, generally weekly (Tuesday)
            # Find the next Tuesday
            days_until_tuesday = (1 - today.weekday() + 7) % 7
            if days_until_tuesday == 0 and today.hour >= 15: # If today is Tuesday after 3 PM, go to next Tuesday
                days_until_tuesday = 7 
            elif days_until_tuesday == 0: # If today is Tuesday before 3 PM, take today
                pass
            next_expiry = today + timedelta(days=days_until_tuesday)
        else: # Stocks, generally monthly (last Thursday of the month)
            # Find the last Thursday of the current or next month
            year = today.year
            month = today.month
            
            # Check if current month's last Thursday has passed
            last_day_of_month = monthrange(year, month)[1]
            temp_date = datetime(year, month, last_day_of_month)
            days_since_last_thursday = (temp_date.weekday() - 3 + 7) % 7 # Days from last Thursday to last day of month
            last_thursday_of_month_date = temp_date - timedelta(days=days_since_last_thursday)
            
            if last_thursday_of_month_date.date() < today.date() or \
               (last_thursday_of_month_date.date() == today.date() and today.hour >= 15):
                # If last Thursday of current month has passed, go to next month
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                last_day_of_month = monthrange(year, month)[1]
                temp_date = datetime(year, month, last_day_of_month)
                days_since_last_thursday = (temp_date.weekday() - 3 + 7) % 7
                last_thursday_of_month_date = temp_date - timedelta(days=days_since_last_thursday)
            
            next_expiry = last_thursday_of_month_date
        
        return next_expiry.strftime("%Y-%m-%d")
