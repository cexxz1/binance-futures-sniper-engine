import uvicorn
from config import load_config

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    print("============================================================")
    print("⚡ MTF Trend Signal Engine — Baslatildi")
    print(f"🔗 Panel: http://127.0.0.1:{cfg.port}")
    print("============================================================")
    uvicorn.run("app:app", host=cfg.host, port=cfg.port, log_level="info")
