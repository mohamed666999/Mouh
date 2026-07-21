from fastapi import FastAPI, Request
import time
import hashlib
import hmac
import json
import requests
from decimal import Decimal, ROUND_DOWN

app = FastAPI()

API_KEY = "Bld82CzzFzxIF65j4O"
API_SECRET = "jY435wiXMgBXpeKXscGg12iFCIJn62XlUHDr"

BYBIT_BASE_URL = "https://api.bybit.com"

ORDER_URL = f"{BYBIT_BASE_URL}/v5/order/create"
TICKER_URL = f"{BYBIT_BASE_URL}/v5/market/tickers"
INSTRUMENT_URL = f"{BYBIT_BASE_URL}/v5/market/instruments-info"


def get_signature(timestamp, recv_window, body):
    param_str = timestamp + API_KEY + recv_window + body

    return hmac.new(
        API_SECRET.encode("utf-8"),
        param_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def get_headers(timestamp, recv_window, signature):
    return {
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-SIGN-TYPE": "2",
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json"
    }


@app.post("/trade")
async def trade(request: Request):

    try:

        # ==========================================
        # 1. قراءة الطلب القادم من Make
        # ==========================================

        data = await request.json()

        action = str(data.get("action", "BUY")).upper()
        symbol = str(data.get("symbol", "DOGEUSDT")).upper()
        amount_usdt = Decimal(str(data.get("amount_usdt", 6)))


        if action not in ["BUY", "SELL"]:
            return {
                "success": False,
                "error": "action يجب أن يكون BUY أو SELL"
            }


        if amount_usdt <= 0:
            return {
                "success": False,
                "error": "amount_usdt يجب أن يكون أكبر من صفر"
            }


        # ==========================================
        # 2. جلب سعر العملة الحالية
        # ==========================================

        ticker_response = requests.get(
            TICKER_URL,
            params={
                "category": "linear",
                "symbol": symbol
            },
            timeout=15
        )

        ticker_data = ticker_response.json()

        if ticker_data.get("retCode") != 0:
            return {
                "success": False,
                "error": "فشل في جلب السعر",
                "details": ticker_data
            }


        ticker_list = ticker_data["result"]["list"]

        if not ticker_list:
            return {
                "success": False,
                "error": f"لم يتم العثور على الرمز {symbol}"
            }


        current_price = Decimal(
            ticker_list[0]["lastPrice"]
        )


        # ==========================================
        # 3. جلب قواعد العملة من Bybit
        # ==========================================

        instrument_response = requests.get(
            INSTRUMENT_URL,
            params={
                "category": "linear",
                "symbol": symbol
            },
            timeout=15
        )

        instrument_data = instrument_response.json()

        if instrument_data.get("retCode") != 0:
            return {
                "success": False,
                "error": "فشل في جلب معلومات العملة",
                "details": instrument_data
            }


        instrument_list = instrument_data["result"]["list"]

        if not instrument_list:
            return {
                "success": False,
                "error": f"لم يتم العثور على معلومات {symbol}"
            }


        instrument = instrument_list[0]

        lot_size = instrument["lotSizeFilter"]

        qty_step = Decimal(
            lot_size["qtyStep"]
        )

        min_order_qty = Decimal(
            lot_size["minOrderQty"]
        )


        # ==========================================
        # 4. حساب كمية العملة حسب amount_usdt
        # ==========================================

        raw_qty = amount_usdt / current_price


        # تقريب الكمية حسب قواعد Bybit
        qty = (
            raw_qty / qty_step
        ).to_integral_value(
            rounding=ROUND_DOWN
        ) * qty_step


        # التأكد من الحد الأدنى للكمية
        if qty < min_order_qty:

            qty = (
                min_order_qty / qty_step
            ).to_integral_value(
                rounding=ROUND_DOWN
            ) * qty_step


        order_value = qty * current_price


        # ==========================================
        # 5. التحقق من الحد الأدنى 5 USDT
        # ==========================================

        if order_value < Decimal("5"):

            return {
                "success": False,
                "error": "قيمة الصفقة أقل من الحد الأدنى 5 USDT",
                "symbol": symbol,
                "current_price": str(current_price),
                "calculated_qty": str(qty),
                "order_value_usdt": str(order_value),
                "minimum_required": "5 USDT"
            }


        # ==========================================
        # 6. إنشاء أمر التداول
        # ==========================================

        side = "Buy" if action == "BUY" else "Sell"


        payload = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": format(qty, "f"),
            "positionIdx": 0
        }


        body = json.dumps(
            payload,
            separators=(",", ":")
        )


        # ==========================================
        # 7. توقيع الطلب
        # ==========================================

        timestamp = str(
            int(time.time() * 1000)
        )

        recv_window = "5000"


        signature = get_signature(
            timestamp,
            recv_window,
            body
        )


        headers = get_headers(
            timestamp,
            recv_window,
            signature
        )


        # ==========================================
        # 8. إرسال الطلب إلى Bybit
        # ==========================================

        response = requests.post(
            ORDER_URL,
            headers=headers,
            data=body,
            timeout=20
        )


        bybit_response = response.json()


        # ==========================================
        # 9. النتيجة
        # ==========================================

        return {

            "success": bybit_response.get("retCode") == 0,

            "action": action,

            "symbol": symbol,

            "amount_usdt_requested": str(amount_usdt),

            "current_price": str(current_price),

            "calculated_qty": str(qty),

            "actual_order_value_usdt": str(order_value),

            "bybit_response": bybit_response

        }


    except Exception as e:

        return {

            "success": False,

            "error": str(e)

        }
