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
ORDER_STATUS_URL = f"{BYBIT_BASE_URL}/v5/order/realtime"
POSITION_URL = f"{BYBIT_BASE_URL}/v5/position/list"


def create_signature(timestamp, recv_window, body):
    param_str = timestamp + API_KEY + recv_window + body

    return hmac.new(
        API_SECRET.encode("utf-8"),
        param_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def create_headers(timestamp, recv_window, signature):
    return {
        "X-BAPI-API-KEY": API_KEY,
        "X-BAPI-SIGN": signature,
        "X-BAPI-SIGN-TYPE": "2",
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "Content-Type": "application/json"
    }


def signed_get(url, params):
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    query_string = "&".join(
        f"{key}={value}"
        for key, value in params.items()
    )

    param_str = timestamp + API_KEY + recv_window + query_string

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
        "X-BAPI-RECV-WINDOW": recv_window
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=20
    )

    return response.json()


@app.get("/")
async def home():
    return {
        "status": "online",
        "service": "Trading Bot"
    }


@app.post("/trade")
async def trade(request: Request):

    try:

        data = await request.json()

        action = str(
            data.get("action", "LONG")
        ).upper()

        symbol = str(
            data.get("symbol", "DOGEUSDT")
        ).upper()

        amount_usdt = Decimal(
            str(data.get("amount_usdt", 6))
        )


        if action not in ["LONG", "SHORT"]:

            return {
                "success": False,
                "error": "action يجب أن يكون LONG أو SHORT"
            }


        if amount_usdt <= 0:

            return {
                "success": False,
                "error": "amount_usdt يجب أن يكون أكبر من صفر"
            }


        ticker_response = requests.get(

            TICKER_URL,

            params={
                "category": "linear",
                "symbol": symbol
            },

            timeout=20

        )

        ticker_data = ticker_response.json()


        if ticker_data.get("retCode") != 0:

            return {

                "success": False,

                "error": "فشل في جلب السعر",

                "details": ticker_data

            }


        ticker_list = ticker_data.get(
            "result", {}
        ).get(
            "list", []
        )


        if not ticker_list:

            return {

                "success": False,

                "error": f"لم يتم العثور على {symbol}"

            }


        current_price = Decimal(

            ticker_list[0]["lastPrice"]

        )


        instrument_response = requests.get(

            INSTRUMENT_URL,

            params={
                "category": "linear",
                "symbol": symbol
            },

            timeout=20

        )

        instrument_data = instrument_response.json()


        if instrument_data.get("retCode") != 0:

            return {

                "success": False,

                "error": "فشل في جلب معلومات العملة",

                "details": instrument_data

            }


        instrument_list = instrument_data.get(

            "result", {}

        ).get(

            "list", []

        )


        if not instrument_list:

            return {

                "success": False,

                "error": f"لم يتم العثور على قواعد {symbol}"

            }


        instrument = instrument_list[0]

        lot_size = instrument["lotSizeFilter"]


        qty_step = Decimal(

            lot_size["qtyStep"]

        )


        min_order_qty = Decimal(

            lot_size["minOrderQty"]

        )


        raw_qty = amount_usdt / current_price


        qty = (

            raw_qty / qty_step

        ).to_integral_value(

            rounding=ROUND_DOWN

        ) * qty_step


        if qty < min_order_qty:

            qty = (

                min_order_qty / qty_step

            ).to_integral_value(

                rounding=ROUND_DOWN

            ) * qty_step


        order_value = qty * current_price


        if order_value < Decimal("5"):

            return {

                "success": False,

                "error": "قيمة الصفقة أقل من الحد الأدنى 5 USDT",

                "symbol": symbol,

                "current_price": str(current_price),

                "calculated_qty": str(qty),

                "order_value_usdt": str(order_value)

            }


        side = (

            "Buy"

            if action == "LONG"

            else "Sell"

        )


        order_link_id = (

            f"BOT_{symbol}_{int(time.time() * 1000)}"

        )


        payload = {

            "category": "linear",

            "symbol": symbol,

            "side": side,

            "orderType": "Market",

            "qty": format(qty, "f"),

            "positionIdx": 0,

            "orderLinkId": order_link_id

        }


        body = json.dumps(

            payload,

            separators=(",", ":")

        )


        timestamp = str(

            int(time.time() * 1000)

        )

        recv_window = "5000"


        signature = create_signature(

            timestamp,

            recv_window,

            body

        )


        headers = create_headers(

            timestamp,

            recv_window,

            signature

        )


        response = requests.post(

            ORDER_URL,

            headers=headers,

            data=body,

            timeout=20

        )


        bybit_response = response.json()


        if bybit_response.get("retCode") != 0:

            return {

                "success": False,

                "action": action,

                "symbol": symbol,

                "bybit_response": bybit_response

            }


        order_id = (

            bybit_response

            .get("result", {})

            .get("orderId")

        )


        time.sleep(1)


        order_status_data = signed_get(

            ORDER_STATUS_URL,

            {

                "category": "linear",

                "symbol": symbol,

                "orderId": order_id

            }

        )


        order_list = (

            order_status_data

            .get("result", {})

            .get("list", [])

        )


        order_status = None


        if order_list:

            order_status = order_list[0].get(

                "orderStatus"

            )


        position_data = signed_get(

            POSITION_URL,

            {

                "category": "linear",

                "symbol": symbol

            }

        )


        positions = (

            position_data

            .get("result", {})

            .get("list", [])

        )


        active_positions = [

            position

            for position in positions

            if Decimal(

                position.get("size", "0")

            ) > 0

        ]


        return {

            "success": True,

            "action": action,

            "symbol": symbol,

            "amount_usdt_requested": str(

                amount_usdt

            ),

            "current_price": str(

                current_price

            ),

            "calculated_qty": str(

                qty

            ),

            "actual_order_value_usdt": str(

                order_value

            ),

            "order_id": order_id,

            "order_status": order_status,

            "active_positions": active_positions,

            "bybit_response": bybit_response,

            "order_status_response": order_status_data

        }


    except Exception as e:

        return {

            "success": False,

            "error": str(e)

        }
