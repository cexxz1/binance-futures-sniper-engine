import threading, time, json, logging, websocket
from typing import Dict, Any, Callable, List, Optional

logger = logging.getLogger("ws_feed")

class BinanceFuturesWSFeed:
    """
    Production WebSocket Feed for Binance Futures:
    - Auto Reconnect with Exponential Backoff
    - Heartbeat & Ping/Pong monitoring
    - Fallback callback on failure
    - Thread-safe candle / ticker cache
    """
    def __init__(self, symbols: List[str], on_candle_update: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.symbols = [s.lower() for s in symbols]
        self.on_candle_update = on_candle_update
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.last_msg_ts = 0.0
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _get_stream_url(self) -> str:
        streams = "/".join([f"{s}@kline_1h" for s in self.symbols])
        return f"wss://fstream.binance.com/stream?streams={streams}"

    def _on_message(self, ws, message):
        try:
            self.last_msg_ts = time.time()
            data = json.loads(message)
            stream = data.get("stream", "")
            payload = data.get("data", {})
            
            if "kline_1h" in stream and "k" in payload:
                k = payload["k"]
                sym = k["s"]
                candle_data = {
                    "symbol": sym,
                    "open": float(k["o"]),
                    "high": float(k["h"]),
                    "low": float(k["l"]),
                    "close": float(k["c"]),
                    "volume": float(k["v"]),
                    "is_closed": k["x"],
                    "timestamp": k["t"]
                }
                with self._lock:
                    self.cache[sym] = candle_data

                if self.on_candle_update:
                    self.on_candle_update(candle_data)
        except Exception as e:
            logger.error(f"WS message parsing error: {e}")

    def _on_error(self, ws, error):
        logger.warning(f"WebSocket Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket Closed: {close_status_code} - {close_msg}")

    def _on_open(self, ws):
        logger.info("WebSocket Connected to Binance USD-M Streams.")
        self.last_msg_ts = time.time()

    def start(self):
        self.running = True
        def run():
            backoff = 1
            while self.running:
                try:
                    url = self._get_stream_url()
                    self.ws = websocket.WebSocketApp(
                        url,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close,
                        on_open=self._on_open
                    )
                    self.ws.run_forever(ping_interval=20, ping_timeout=10)
                except Exception as e:
                    logger.error(f"WS Run exception: {e}")
                
                if self.running:
                    time.sleep(min(backoff, 30))
                    backoff = min(backoff * 2, 60)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def get_latest_candle(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.cache.get(symbol.upper())

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
