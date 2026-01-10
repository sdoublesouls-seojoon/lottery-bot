import os
import sys
from dotenv import load_dotenv

import auth
import lotto645
# import win720  # 연금복권 사용 안 함
import notification
import time


def buy_lotto645(authCtrl: auth.AuthController, cnt: int, mode: str):
    lotto = lotto645.Lotto645()
    _mode = lotto645.Lotto645Mode[mode.upper()]
    response = lotto.buy_lotto645(authCtrl, cnt, _mode)
    response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
    return response

def check_winning_lotto645(authCtrl: auth.AuthController) -> dict:
    lotto = lotto645.Lotto645()
    item = lotto.check_winning(authCtrl)
    return item

# 연금복권 관련 함수 - 사용 안 함
# def buy_win720(authCtrl: auth.AuthController, username: str):
#     pension = win720.Win720()
#     response = pension.buy_Win720(authCtrl, username)
#     response['balance'] = pension.get_balance(auth_ctrl=authCtrl)
#     return response

# def check_winning_win720(authCtrl: auth.AuthController) -> dict:
#     pension = win720.Win720()
#     item = pension.check_winning(authCtrl)
#     return item

def send_message(mode: int, lottery_type: int, response: dict, webhook_url: str, platform: str = "slack"):
    notify = notification.Notification()

    if mode == 0:
        if lottery_type == 0:
            notify.send_lotto_winning_message(response, webhook_url, platform)
        else:
            notify.send_win720_winning_message(response, webhook_url, platform)
    elif mode == 1: 
        if lottery_type == 0:
            notify.send_lotto_buying_message(response, webhook_url, platform)
        else:
            notify.send_win720_buying_message(response, webhook_url, platform)

def check():
    load_dotenv()

    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL') 
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    
    # Slack 우선, 없으면 Discord 사용
    webhook_url = slack_webhook_url or discord_webhook_url
    platform = "slack" if slack_webhook_url else "discord"

    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)
    
    response = check_winning_lotto645(globalAuthCtrl)
    send_message(0, 0, response=response, webhook_url=webhook_url, platform=platform)

    # 연금복권 당첨 확인 - 사용 안 함
    # time.sleep(10)
    # response = check_winning_win720(globalAuthCtrl)
    # send_message(0, 1, response=response, webhook_url=webhook_url, platform=platform)

def buy(): 
    
    load_dotenv() 

    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    count = int(os.environ.get('COUNT', '1'))
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL') 
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    
    # 구매 모드: auto 또는 manual
    purchase_mode = os.environ.get('PURCHASE_MODE', 'auto').lower()
    sheet_api_url = os.environ.get('SHEET_API_URL', '')
    
    # Slack 우선, 없으면 Discord 사용
    webhook_url = slack_webhook_url or discord_webhook_url
    platform = "slack" if slack_webhook_url else "discord"

    # Selenium 브라우저 자동화 모드 사용
    from selenium_lotto import run_selenium_buy
    
    result = run_selenium_buy(
        user_id=username,
        password=password,
        count=count,
        sheet_api_url=sheet_api_url if purchase_mode == "manual" else None,
        mode=purchase_mode
    )
    
    
    # 결과 출력
    if result["success"]:
        print(f"✓ Selenium 실행 성공: {result['message']}")
        if result.get("games"):
            print(f"   선택된 게임: {len(result['games'])}개")
    else:
        print(f"❌ Selenium 실행 실패: {result['message']}")
        
    # 알림 전송
    notify = notification.Notification()
    notify.send_selenium_buy_message(result, webhook_url, platform)

def run():
    if len(sys.argv) < 2:
        print("Usage: python controller.py [buy|check]")
        return

    if sys.argv[1] == "buy":
        buy()
    elif sys.argv[1] == "check":
        check()
  

if __name__ == "__main__":
    run()
