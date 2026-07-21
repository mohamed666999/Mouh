from fastapi import FastAPI, Request
import time
import hashlib
import hmac
import json
import os
import requests

app = FastAPI()

API_KEY = os.getenv("Bld82CzzFzxIF65j4O")
API_SECRET = os.getenv("jY435wiXMgBXpeKXscGg12iFCIJn62XlUHDr")

BYBIT_URL = "https://api.bybit.com/v5/order/create"


@app.post("/trade")
async def trade(request: Request):
    try:
        data = await request.json()

        action = data.get("action", "BUY")
        symbol = data.get("symbol", "DOGEUSDT")
        amount_usdt = float(data.get("amount_usdt", 6))

        # مثال: الكمية يجب أن تكون محسوبة حسب سعر DOGE
        # هذا الجزء يحتاج سعر السوق
        qty = str(data.get("qty", "40"))

        side = "Buy" if action.upper() == "BUY" else "Sell"

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"

        payload = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": qty,
            "positionIdx": 0
        }

        body = json.dumps(payload, separators=(",", ":"))

        param_str = timestamp + API_KEY + recv_window + body

        signature = hmac.new(
            API_SECRET.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "X-BAPI-API-KEY": API_KEY,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json"
        }

        response = requests.post(
            BYBIT_URL,
            headers=headers,
            data=body
        )

        return {
            "success": response.status_code == 200,
            "bybit_response": response.json()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
