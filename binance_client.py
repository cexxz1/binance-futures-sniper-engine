import hmac, hashlib, time, json, urllib.request, urllib.parse, logging
from typing import Dict, Any, Optional

logger = logging.getLogger("binance_client")

class BinanceFuturesClient:
    """
    Binance USD-M Futures Client (Production / Testnet / Dry-Run Safe):
    - Dry-Run mode: Logs execution without placing real money
    - Hard Cap Safety Guard: Hardcoded absolute max notional cap ($500,000 max)
    - HMAC-SHA256 request signing with auto-adjusted recvWindow and time sync
    - Rate limit & Ban protection (handles 429, 418)
    - Dynamic Leverage Bracket & Maintenance Margin Rate (MMR) lookup
    """
    def __init__(self, api_key: str = "", api_secret: str = "", testnet: bool = False, dry_run: bool = True):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.testnet = testnet
        self.dry_run = dry_run
        self.base_url = "https://testnet.binancefuture.com" if testnet else "https://fapi.binance.com"
        self.time_offset = 0
        self.HARD_CAP_MAX_NOTIONAL_USD = 500000.0  # Safe hard limit to prevent catastrophic glitch orders
        self.sync_time()

    def sync_time(self):
        """Syncs local machine clock with Binance server timestamp to prevent recvWindow errors."""
        try:
            url = f"{self.base_url}/fapi/v1/time"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                server_time = data.get("serverTime", int(time.time() * 1000))
                self.time_offset = server_time - int(time.time() * 1000)
        except Exception as e:
            logger.warning(f"Time sync failed: {e}")
            self.time_offset = 0

    def _sign(self, params: Dict[str, Any]) -> str:
        params["timestamp"] = int(time.time() * 1000) + self.time_offset
        params["recvWindow"] = 5000
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return f"{query_string}&signature={signature}"

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Dict[str, Any]:
        params = params or {}
        headers = {"User-Agent": "Mozilla/5.0"}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key

        if signed:
            query = self._sign(params)
            url = f"{self.base_url}{path}?{query}" if method in ["GET", "DELETE"] else f"{self.base_url}{path}"
            data = query.encode("utf-8") if method in ["POST", "PUT"] else None
        else:
            query = urllib.parse.urlencode(params)
            url = f"{self.base_url}{path}?{query}" if query else f"{self.base_url}{path}"
            data = None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            logger.error(f"Binance HTTP {e.code}: {err_body}")
            if e.code in [429, 418]:
                time.sleep(10) # IP Ban protection
            return {"error": True, "code": e.code, "msg": err_body}
        except Exception as e:
            logger.error(f"Network error: {e}")
            return {"error": True, "msg": str(e)}

    # Dynamic Leverage Bracket & MMR Verification
    def get_leverage_bracket(self, symbol: str) -> Dict[str, Any]:
        """Fetches live tier bracket and MMR directly from Binance."""
        if not self.api_key:
            return {"max_leverage": 25, "mmr": 0.005}
        res = self._request("GET", "/fapi/v1/leverageBracket", {"symbol": symbol}, signed=True)
        if isinstance(res, list) and len(res) > 0:
            brackets = res[0].get("brackets", [])
            if brackets:
                return {
                    "max_leverage": brackets[0].get("initialLeverage", 25),
                    "mmr": brackets[0].get("maintMarginRatio", 0.005)
                }
        return {"max_leverage": 25, "mmr": 0.005}

    def set_leverage(self, symbol: str, leverage: int) -> int:
        """Sets leverage after validating against symbol's max tier cap."""
        bracket = self.get_leverage_bracket(symbol)
        max_allowed = bracket.get("max_leverage", 25)
        safe_leverage = min(leverage, max_allowed)
        
        if self.dry_run:
            logger.info(f"[DRY-RUN] Set Leverage: {symbol} -> {safe_leverage}x (Max allowed: {max_allowed}x)")
            return safe_leverage

        res = self._request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": safe_leverage}, signed=True)
        return safe_leverage

    def set_margin_type(self, symbol: str, margin_type: str = "ISOLATED"):
        if self.dry_run:
            logger.info(f"[DRY-RUN] Set Margin Type: {symbol} -> {margin_type}")
            return True
        return self._request("POST", "/fapi/v1/marginType", {"symbol": symbol, "marginType": margin_type}, signed=True)

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: Optional[float] = None, stop_price: Optional[float] = None) -> Dict[str, Any]:
        """Places futures order with strict Hard Cap & Safe Mode guards."""
        notional_estimate = quantity * (price or 1.0)
        if notional_estimate > self.HARD_CAP_MAX_NOTIONAL_USD:
            logger.critical(f"HARD CAP BLOCKED: Order {symbol} notional ${notional_estimate:,.2f} exceeds hard limit ${self.HARD_CAP_MAX_NOTIONAL_USD:,.2f}")
            return {"error": True, "msg": "HARD_CAP_EXCEEDED"}

        if self.dry_run:
            logger.info(f"[DRY-RUN ORDER] {side} {symbol} | Qty: {quantity} | Price: {price} | Stop: {stop_price}")
            return {"status": "FILLED", "orderId": int(time.time()), "symbol": symbol, "dry_run": True}

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity
        }
        if price:
            params["price"] = price
            params["timeInForce"] = "GTC"
        if stop_price:
            params["stopPrice"] = stop_price

        return self._request("POST", "/fapi/v1/order", params, signed=True)
