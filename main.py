# ----------------------------------------------- #
# Plugin Name           : TradingView-Webhook-Bot #
# Author Name           : fabston                 #
# File Name             : main.py                 #
# ----------------------------------------------- #

import json
import time

from flask import Flask, request

import config
from handler import *

app = Flask(__name__)
import nest_asyncio

def get_timestamp():
    timestamp = time.strftime("%Y-%m-%d %X")
    return timestamp


@app.route("/webhook", methods=["POST"])
async def webhook():
    try:
        if request.method == "POST":
            data = request.get_json()
            print(data)
            key = data["key"]
            print("key",key)
            
            if key == config.sec_key:
                
                print(get_timestamp(), "Alert Received & Sent!")
                
                await process_alert(data)
                
                return "Sent alert", 200

            else:
                print("[X]", get_timestamp(), "Alert Received & Refused! (Wrong Key)")
                return "Refused alert", 400

    except Exception as e:
        print("[X]", get_timestamp(), "Error:\n>", e)
        return "Error", 400


if __name__ == "__main__":
    from waitress import serve
    
    nest_asyncio.apply()

    serve(app, host="0.0.0.0", port=80)
