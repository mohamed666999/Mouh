from fastapi import FastAPI, Request
import time
import hashlib
import hmac
import json

app = FastAPI()

API_KEY = "Bld82CzzFzxIF65j4O"
API_SECRET = "jY435wiXMgBXpeKXscGg12iFCIJn62XlUHDr"

@app.post("/trade")
async def trade(request: Request):
    try:
        data = await request.json()
        symbol = data.get("symbol", "DOGEUSDT")
        side = data.get("side", "Buy")
        qty = data.get("qty", "40")

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        payload = {
            "category": "linear",
            "symbol": symbol,
            "side": side.capitalize(),
            "orderType": "Market",
            "qty": str(qty),
            "positionIdx": 0
        }
        
        payload_str = json.dumps(payload)
        param_str = timestamp + API_KEY + recv_window + payload_str
        
        # إنشاء التوقيع الأمني
        hash_mac = hmac.new(bytes(API_SECRET, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
        signature = hash_mac.hexdigest()
        
        # إرجاع البيانات جاهزة لـ Make لكي يرسلها هو
        return {
            "success": True,
            "headers": {
                "X-BAPI-API-KEY": API_KEY,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window
            },
            "payload": payload_str
        }
        
    except Exception as e:
        return {"error": "حدث خطأ", "message": str(e)}
