import datetime
import json

from datetime import timedelta
from enum import Enum

from bs4 import BeautifulSoup as BS

import auth
from HttpClient import HttpClientSingleton

class Lotto645Mode(Enum):
    AUTO = 1
    MANUAL = 2
    BUY = 10 
    CHECK = 20

class Lotto645:

    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        "sec-ch-ua-mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "Origin": "https://ol.dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://ol.dhlottery.co.kr/olotto/game/game645.do",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
    }

    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    def buy_lotto645(
        self, 
        auth_ctrl: auth.AuthController, 
        cnt: int, 
        mode: Lotto645Mode
    ) -> dict:
        assert type(auth_ctrl) == auth.AuthController
        assert type(cnt) == int and 1 <= cnt <= 5
        assert type(mode) == Lotto645Mode

        headers = self._generate_req_headers(auth_ctrl)
        requirements = self._getRequirements(headers)

        data = (
            self._generate_body_for_auto_mode(cnt, requirements)
            if mode == Lotto645Mode.AUTO
            else self._generate_body_for_manual(cnt)
        )

        body = self._try_buying(headers, data)

        self._show_result(body)
        return body

    def _generate_req_headers(self, auth_ctrl: auth.AuthController) -> dict:
        assert type(auth_ctrl) == auth.AuthController

        return auth_ctrl.add_auth_cred_to_headers(self._REQ_HEADERS)

    def _generate_body_for_auto_mode(self, cnt: int, requirements: list) -> dict:
        assert type(cnt) == int and 1 <= cnt <= 5

        SLOTS = [
            "A",
            "B",
            "C",
            "D",
            "E",
        ]  

        return {
            "round": self._get_round(),
            "direct": requirements[0],  # TODO: test if this can be comment
            "nBuyAmount": str(1000 * cnt),
            "param": json.dumps(
                [
                    {"genType": "0", "arrGameChoiceNum": None, "alpabet": slot}
                    for slot in SLOTS[:cnt]
                ]
            ),
            'ROUND_DRAW_DATE' : requirements[1],
            'WAMT_PAY_TLMT_END_DT' : requirements[2],
            "gameCnt": cnt
        }

    def _generate_body_for_manual(self, cnt: int) -> dict:
        assert type(cnt) == int and 1 <= cnt <= 5

        raise NotImplementedError()

    def _getRequirements(self, headers: dict) -> list: 
        org_headers = headers.copy()

        headers["Referer"] ="https://ol.dhlottery.co.kr/olotto/game/game645.do"
        headers["Content-Type"] = "application/json; charset=UTF-8"
        headers["X-Requested-With"] ="XMLHttpRequest"


		#no param needed at now
        res = self.http_client.post(
            url="https://ol.dhlottery.co.kr/olotto/game/egovUserReadySocket.json", 
            headers=headers
        )
        
        direct = json.loads(res.text)["ready_ip"]

        # game645.do 호출 (로그인 시 이미 세션 초기화됨)
        print(f"Calling game645.do...")
        res = self.http_client.get(
            url="https://ol.dhlottery.co.kr/olotto/game/game645.do",
            headers=org_headers
        )
        html = res.text

        # 디버깅: HTML 파일 저장 (GitHub Actions Artifacts용)
        import os
        debug_dir = os.getenv('GITHUB_WORKSPACE', '.')
        debug_file = os.path.join(debug_dir, 'game645_debug.html')
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"✓ HTML saved to {debug_file} (size: {len(html)} bytes)")
        except Exception as e:
            print(f"Warning: Could not save HTML: {e}")

        # 세션 만료 확인
        if "시간 초과" in html or "세션이 해제" in html or "로그인해 주시기 바랍니다" in html:
            print(f"ERROR: Session expired! Please check login credentials.")
            print(f"This usually means the login session cookies are not being shared across subdomains.")
            raise ValueError("Session expired. Login session was not properly maintained.")

        # 디버깅: 기본 정보
        print(f"✓ game645.do response: {res.status_code}, {len(html)} bytes")

        soup = BS(html, "html5lib")

        draw_date_input = soup.find("input", id="ROUND_DRAW_DATE")
        tlmt_date_input = soup.find("input", id="WAMT_PAY_TLMT_END_DT")

        if not draw_date_input or not tlmt_date_input:
            print(f"ERROR: Required input fields not found in HTML!")
            print(f"ROUND_DRAW_DATE: {draw_date_input}")
            print(f"WAMT_PAY_TLMT_END_DT: {tlmt_date_input}")

            # 사용 가능한 input 태그 출력 (디버깅용)
            print(f"Available input tags (first 10):")
            all_inputs = soup.find_all("input", limit=10)
            for inp in all_inputs:
                print(f"  - id={inp.get('id')}, name={inp.get('name')}, type={inp.get('type')}")

            raise ValueError("Required form inputs not found in game645.do page")
        
        draw_date = draw_date_input.get('value')
        tlmt_date = tlmt_date_input.get('value')

        print(f"✓ Found ROUND_DRAW_DATE: {draw_date}")
        print(f"✓ Found WAMT_PAY_TLMT_END_DT: {tlmt_date}")

        return [direct, draw_date, tlmt_date]

    def _get_round(self) -> str:
        res = self.http_client.get("https://www.dhlottery.co.kr/common.do?method=main")
        html = res.text
        soup = BS(
            html, "html5lib"
        )  # 'html5lib' : in case that the html don't have clean tag pairs
        last_drawn_round = int(soup.find("strong", id="lottoDrwNo").text)
        return str(last_drawn_round + 1)

    def get_balance(self, auth_ctrl: auth.AuthController) -> str: 

        headers = self._generate_req_headers(auth_ctrl)
        res = self.http_client.post(
            url="https://dhlottery.co.kr/userSsl.do?method=myPage", 
            headers=headers
        )

        html = res.text
        soup = BS(
            html, "html5lib"
        )
        balance = soup.find("p", class_="total_new").find('strong').text
        return balance
        
    def _try_buying(self, headers: dict, data: dict) -> dict:
        assert type(headers) == dict
        assert type(data) == dict

        headers["Content-Type"]  = "application/x-www-form-urlencoded; charset=UTF-8"

        res = self.http_client.post(
            "https://ol.dhlottery.co.kr/olotto/game/execBuy.do",
            headers=headers,
            data=data,
        )
        res.encoding = "utf-8"
        return json.loads(res.text)

    def check_winning(self, auth_ctrl: auth.AuthController) -> dict:
        assert type(auth_ctrl) == auth.AuthController

        headers = self._generate_req_headers(auth_ctrl)

        parameters = self._make_search_date()

        data = {
            "nowPage": 1, 
            "searchStartDate": parameters["searchStartDate"],
            "searchEndDate": parameters["searchEndDate"],
            "winGrade": 2,
            "lottoId": "LO40", 
            "sortOrder": "DESC"
        }

        result_data = {
            "data": "no winning data"
        }

        try:
            res = self.http_client.post(
                "https://dhlottery.co.kr/myPage.do?method=lottoBuyList",
                headers=headers,
                data=data
            )

            html = res.text
            soup = BS(html, "html5lib")

            winnings = soup.find("table", class_="tbl_data tbl_data_col").find_all("tbody")[0].find_all("td")

            get_detail_info = winnings[3].find("a").get("href")

            order_no, barcode, issue_no = get_detail_info.split("'")[1::2]
            url = f"https://dhlottery.co.kr/myPage.do?method=lotto645Detail&orderNo={order_no}&barcode={barcode}&issueNo={issue_no}"

            response = self.http_client.get(url)

            soup = BS(response.text, "html5lib")

            lotto_results = []

            for li in soup.select("div.selected li"):
                label = li.find("strong").find_all("span")[0].text.strip()
                status = li.find("strong").find_all("span")[1].text.strip().replace("낙첨","0등")
                nums = li.select("div.nums > span")

                status = " ".join(status.split())

                formatted_nums = []
                for num in nums:
                    ball = num.find("span", class_="ball_645")
                    if ball:
                        formatted_nums.append(f"✨{ball.text.strip()}")
                    else:
                        formatted_nums.append(num.text.strip())

                lotto_results.append({
                    "label": label,
                    "status": status,
                    "result": formatted_nums
                })

            if len(winnings) == 1:
                return result_data

            result_data = {
                "round": winnings[2].text.strip(),
                "money": winnings[6].text.strip(),
                "purchased_date": winnings[0].text.strip(),
                "winning_date": winnings[7].text.strip(),
                "lotto_details": lotto_results
            }
        except:
            pass

        return result_data
    
    def _make_search_date(self) -> dict:
        today = datetime.datetime.today()
        today_str = today.strftime("%Y%m%d")
        weekago = today - timedelta(days=7)
        weekago_str = weekago.strftime("%Y%m%d")
        return {
            "searchStartDate": weekago_str,
            "searchEndDate": today_str
        }

    def _show_result(self, body: dict) -> None:
        assert type(body) == dict

        if body.get("loginYn") != "Y":
            return

        result = body.get("result", {})
        if result.get("resultMsg", "FAILURE").upper() != "SUCCESS":    
            return
