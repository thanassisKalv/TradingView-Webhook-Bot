# ----------------------------------------------- #
# Plugin Name           : TradingView-Webhook-Bot #
# Author Name           : fabston                 #
# File Name             : handler.py              #
# ----------------------------------------------- #

import smtplib
import ssl
from email.mime.text import MIMEText

import tweepy
from discord_webhook import DiscordEmbed, DiscordWebhook
from slack_webhook import Slack
from telegram import Bot
import json
import config

from ib_insync import *

PORT = 7497    
ACCOUNT_ID =  "DU5981186"


# util function to ensure that 
def price_round(x, target):
    # print("Rounding:", x, target)
    target = float(1/target)
    rounded = round(x*target)/target
    return rounded

def save_trade_data(tradeData:Trade):
    saveData = {
        "contract": str(tradeData.contract),
        "order": str(tradeData.order),
        "orderStatus": str(tradeData.orderStatus)
    }
    with open("trades-"+ACCOUNT_ID+".json", 'a') as logFile:
        json.dump(saveData, logFile)

def execute_ib_trade(ib:IB, data):
    # Extract the relevant information from the alert data
    symbol = data['symbol']
    action = data['action']
    orderType = data['type']
    quantity = int(data['quantity'])
    lmtPrice = float(data['limitPrice'])

    # Define the order parameters
    contract = Stock(symbol, 'SMART', 'USD')

    if orderType == "LMT":
        [contractDetails] = ib.reqContractDetails(contract)
        minTick = contractDetails.minTick * contractDetails.priceMagnifier
        lmtPrice = price_round(lmtPrice, minTick)
    
    order = MarketOrder(action, quantity)
    if orderType == "LMT":
        order = LimitOrder(action, quantity, lmtPrice)

    ib.qualifyContracts(contract)

    trade = ib.placeOrder(contract, order)
    ib.sleep(1)  # some waiting time before saving trade/order status

    save_trade_data(trade)


# connect to Interactive Broker through TWS localhost
def ib_connect(port) -> IB:
    ib = IB()
    ib.connect('host.docker.internal', port, 1, account=ACCOUNT_ID)
    # data for Paper or Live Trading
    # ib.reqMarketDataType(3)
    return ib

def logError(reqId, errorCode, errorString, contract):
        print(reqId, errorCode, errorString)
        with open("error-logs-"+ACCOUNT_ID+".txt", 'a') as logFile:
            error_msg = f"ReqId:{reqId} received error code:{errorCode} with error description:{errorString}"
            logFile.write(str(error_msg)+"\n")

async def process_alert(alertData: dict):
    msg = alertData["msg"].encode("latin-1", "backslashreplace").decode("unicode_escape")
    print("Just print the message:", msg)

    if config.execute_ib_trades:
        print("Executing IB trade")

        ib_client = ib_connect(PORT)

        ib_client.errorEvent += logError

        execute_ib_trade(ib_client, alertData)

        ib_client.disconnect()

    if config.send_telegram_alerts:
        tg_bot = Bot(token=config.tg_token)
        try:
            tg_bot.sendMessage(
                data["telegram"],
                msg,
                parse_mode="MARKDOWN",
            )
        except KeyError:
            tg_bot.sendMessage(
                config.channel,
                msg,
                parse_mode="MARKDOWN",
            )
        except Exception as e:
            print("[X] Telegram Error:\n>", e)

    if config.send_discord_alerts:
        try:
            webhook = DiscordWebhook(
                url="https://discord.com/api/webhooks/" + data["discord"]
            )
            embed = DiscordEmbed(title=msg)
            webhook.add_embed(embed)
            webhook.execute()
        except KeyError:
            webhook = DiscordWebhook(
                url="https://discord.com/api/webhooks/" + config.discord_webhook
            )
            embed = DiscordEmbed(title=msg)
            webhook.add_embed(embed)
            webhook.execute()
        except Exception as e:
            print("[X] Discord Error:\n>", e)

    if config.send_slack_alerts:
        try:
            slack = Slack(url="https://hooks.slack.com/services/" + data["slack"])
            slack.post(text=msg)
        except KeyError:
            slack = Slack(
                url="https://hooks.slack.com/services/" + config.slack_webhook
            )
            slack.post(text=msg)
        except Exception as e:
            print("[X] Slack Error:\n>", e)

    if config.send_twitter_alerts:
        tw_auth = tweepy.OAuthHandler(config.tw_ckey, config.tw_csecret)
        tw_auth.set_access_token(config.tw_atoken, config.tw_asecret)
        tw_api = tweepy.API(tw_auth)
        try:
            tw_api.update_status(
                status=msg.replace("*", "").replace("_", "").replace("`", "")
            )
        except Exception as e:
            print("[X] Twitter Error:\n>", e)

    if config.send_email_alerts:
        try:
            email_msg = MIMEText(
                msg.replace("*", "").replace("_", "").replace("`", "")
            )
            email_msg["Subject"] = config.email_subject
            email_msg["From"] = config.email_sender
            email_msg["To"] = config.email_sender
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                config.email_host, config.email_port, context=context
            ) as server:
                server.login(config.email_user, config.email_password)
                server.sendmail(
                    config.email_sender, config.email_receivers, email_msg.as_string()
                )
                server.quit()
        except Exception as e:
            print("[X] Email Error:\n>", e)
