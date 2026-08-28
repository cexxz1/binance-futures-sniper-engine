import yaml
from pathlib import Path
from pydantic import BaseModel, Field

class Config(BaseModel):
    # If symbols is empty or contains "ALL", the engine automatically scans all active USDT Perpetual contracts
    symbols: list[str] = Field(default_factory=lambda: ["ALL"])
    max_symbols_limit: int = 200  # Top N by 24h volume if ALL
    tf_trend: str = "4h"
    tf_entry: str = "1h"
    ema_trend_fast: int = 50
    ema_trend_slow: int = 200
    ema_entry_fast: int = 9
    ema_entry_slow: int = 21
    adx_period: int = 14
    adx_min_trend: float = 20.0
    adx_overextended: float = 70.0
    ribbon_min_spread_pct: float = 0.05  # Ribbon spread threshold
    volume_lookback: int = 20
    volume_multiplier: float = 1.1       # 1.1x volume confirmation
    atr_period: int = 14
    atr_stop_multiplier: float = 1.2
    tp1_r_multiple: float = 1.5
    cooldown_bars: int = 3
    pullback_atr_tolerance: float = 0.5
    
    # Patch v1.1 Settings
    tp_mode: str = "PARTIAL_TRAIL"       # "FULL" or "PARTIAL_TRAIL"
    partial_tp_ratio: float = 0.5        # 50% partial take profit at TP1
    max_hold_bars: int = 48              # MFE based decay threshold
    mfe_min_threshold: float = 0.5       # Min MFE in ATR units to prevent decay
    
    # Binance API Settings
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_rest_base: str = "https://fapi.binance.com"
    binance_ws_base: str = "wss://fstream.binance.com/ws"
    
    # Engine & Server Settings
    host: str = "127.0.0.1"
    port: int = 8080
    db_path: str = "mtf_signals.sqlite"
    poll_interval_seconds: int = 5
    
    # Alerting
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = False
    browser_notifications: bool = True

def load_config(path: str = "config.yaml") -> Config:
    config_file = Path(path)
    if not config_file.exists():
        cfg = Config()
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(cfg.model_dump(), f, default_flow_style=False, sort_keys=False)
        return cfg
    
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return Config(**data)

def save_config(config: Config, path: str = "config.yaml"):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)
