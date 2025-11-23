# metering_agent.py
import hmac, hashlib, json, os, sqlite3, datetime, uuid
from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel
import requests

# --- Configuration (en prod : .env ou secret manager) ---
SHARED_SECRET = os.getenv("METERING_SHARED_SECRET", "dev-secret-key")
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.getenv("PORT", "8000"))
DB_PATH = os.getenv("METER_DB", "metering.db")

# --- DB helper (SQLite simple ledger) ---
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS metering_records (
        id TEXT PRIMARY KEY,
        obp_id TEXT,
        meter_id TEXT,
        timestamp_utc TEXT,
        value_kwh REAL,
        source TEXT,
        signed_payload TEXT,
        raw_json TEXT
    )
    """)
    conn.commit()
    return conn

db = init_db()

def insert_record(obp_id, meter_id, ts, value_kwh, source, signed_payload, raw_json):
    rid = str(uuid.uuid4())
    c = db.cursor()
    c.execute("""
      INSERT INTO metering_records (id, obp_id, meter_id, timestamp_utc, value_kwh, source, signed_payload, raw_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (rid, obp_id, meter_id, ts, value_kwh, source, signed_payload, json.dumps(raw_json)))
    db.commit()
    return rid

# --- Simple HMAC signer/verifier ---
def sign_payload(payload_json: dict):
    payload_bytes = json.dumps(payload_json, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(SHARED_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return sig

def verify_signature(payload_json: dict, signature: str):
    expected = sign_payload(payload_json)
    return hmac.compare_digest(expected, signature)

# --- FastAPI app ---
app = FastAPI(title="Metering Agent")

class MeteringMessage(BaseModel):
    context: dict
    message: dict

# 1) Endpoint to RECEIVE on_metering callbacks (BPP -> BAP style)
@app.post("/on_metering")
async def on_metering(msg: MeteringMessage, x_signature: str | None = Header(None)):
    # Verify signature if present
    payload = msg.dict()
    if x_signature:
        if not verify_signature(payload, x_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # parse expected fields (example schema)
    # message may contain: { "metering": { "obp_id": "...", "meter_id": "...", "value_kwh": 1.23, "timestamp": "..." } }
    meter = payload.get("message", {}).get("metering", {})
    obp_id = meter.get("obp_id") or payload["context"].get("transaction_id")
    meter_id = meter.get("meter_id", "unknown")
    value = meter.get("value_kwh", 0.0)
    ts = meter.get("timestamp") or datetime.datetime.utcnow().isoformat()

    # store in ledger
    sig = x_signature or sign_payload(payload)
    rec_id = insert_record(obp_id, meter_id, ts, value, "on_metering_callback", sig, payload)

    return {"ack": {"status": "ACK", "record_id": rec_id}}

# 2) Admin endpoint to SEND a metering message to a receiver
class SendMeteringRequest(BaseModel):
    target_url: str
    obp_id: str
    meter_id: str
    value_kwh: float

@app.post("/send_metering")
def send_metering(req: SendMeteringRequest):
    # build Beckn-like metering payload
    now = datetime.datetime.utcnow().isoformat()
    msg = {
        "context": {
            "domain": "energy.metering",
            "action": "metering",
            "bpp_id": "metering.agent.example",
            "transaction_id": str(uuid.uuid4()),
            "timestamp": now
        },
        "message": {
            "metering": {
                "obp_id": req.obp_id,
                "meter_id": req.meter_id,
                "value_kwh": req.value_kwh,
                "timestamp": now
            }
        }
    }
    signature = sign_payload(msg)
    headers = {"Content-Type": "application/json", "X-Signature": signature}
    r = requests.post(req.target_url, json=msg, headers=headers, timeout=10)
    # store sent record locally
    insert_record(req.obp_id, req.meter_id, now, req.value_kwh, "sent_metering", signature, msg)
    return {"status_code": r.status_code, "resp_text": r.text}

# 3) Simple report endpoint: compute half-hourly aggregation per meter (P444 style)
@app.get("/report/daily_aggregates")
def daily_aggregates(date: str | None = None):
    # date format YYYY-MM-DD, default today
    if not date:
        date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    c = db.cursor()
    # select all records for that day
    start = f"{date}T00:00:00"
    end = f"{date}T23:59:59"
    c.execute("SELECT meter_id, timestamp_utc, value_kwh, obp_id FROM metering_records WHERE timestamp_utc BETWEEN ? AND ?", (start, end))
    rows = c.fetchall()
    # aggregate per 30-min window (UTC)
    aggregates = {}
    for meter_id, ts, val, obp in rows:
        dt = datetime.datetime.fromisoformat(ts)
        # compute half-hour window key: YYYY-MM-DDTHH:MM where MM = 00 or 30
        minute = 0 if dt.minute < 30 else 30
        window_start = dt.replace(minute=minute, second=0, microsecond=0).isoformat()
        key = (meter_id, window_start)
        aggregates.setdefault(key, {"meter_id": meter_id, "window_start": window_start, "sum_kwh": 0.0, "samples": 0, "obp_ids": set()})
        aggregates[key]["sum_kwh"] += val
        aggregates[key]["samples"] += 1
        aggregates[key]["obp_ids"].add(obp)
    # format
    out = []
    for (meter_id, window_start), info in aggregates.items():
        out.append({
            "meter_id": meter_id,
            "window_start": window_start,
            "sum_kwh": info["sum_kwh"],
            "samples": info["samples"],
            "obp_ids": list(info["obp_ids"])
        })
    return {"date": date, "aggregates": out}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("metering_agent:app", host=LISTEN_HOST, port=LISTEN_PORT, reload=True)
