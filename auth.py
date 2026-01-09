import copy
import json
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from HttpClient import HttpClientSingleton


class AuthController:
    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "Origin": "https://www.dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://www.dhlottery.co.kr/",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
    }

    _AUTH_CRED = ""

    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    def login(self, user_id: str, password: str) -> bool:
        """
        동행복권 로그인 (RSA 암호화 방식)
        
        Args:
            user_id: 사용자 ID
            password: 비밀번호
            
        Returns:
            bool: 로그인 성공 여부
        """
        assert type(user_id) == str
        assert type(password) == str

        # Step 1: 초기 세션 ID 획득
        default_auth_cred = self._get_default_auth_cred()
        
        # Step 2: RSA 공개키 조회
        rsa_key_data = self._get_rsa_public_key(default_auth_cred)
        
        # Step 3: 비밀번호 RSA 암호화
        encrypted_password = self._encrypt_with_rsa(password, rsa_key_data)
        
        # Step 4: 로그인 요청
        headers = self._generate_req_headers(default_auth_cred)
        data = self._generate_body(user_id, encrypted_password)
        
        login_result = self._try_login(headers, data)
        
        # Step 5: 로그인 성공 여부 확인 및 세션 저장
        if login_result.get("result") == "success" or login_result.get("loginYn") == "Y":
            self._update_auth_cred(default_auth_cred)
            return True
        else:
            print(f"Login failed: {login_result.get('message', 'Unknown error')}")
            return False

    def add_auth_cred_to_headers(self, headers: dict) -> dict:
        assert type(headers) == dict

        copied_headers = copy.deepcopy(headers)
        copied_headers["Cookie"] = f"JSESSIONID={self._AUTH_CRED}"
        return copied_headers

    def _get_default_auth_cred(self) -> str:
        """로그인 페이지 접속으로 초기 JSESSIONID 획득"""
        # 로그인 페이지에 접속하여 세션 초기화
        res = self.http_client.get(
            "https://www.dhlottery.co.kr/user.do?method=login"
        )
        
        # 디버깅: 쿠키 정보 출력
        print(f"Response cookies: {list(res.cookies)}")
        print(f"Session cookies: {list(self.http_client.session.cookies)}")
        
        # 세션 쿠키에서 JSESSIONID 추출
        return self._get_j_session_id_from_session()

    def _get_rsa_public_key(self, j_session_id: str) -> dict:
        """
        RSA 공개키 조회
        
        Returns:
            dict: {'rsaModulus': '...', 'publicExponent': '...'}
        """
        headers = self._generate_req_headers(j_session_id)
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        headers["X-Requested-With"] = "XMLHttpRequest"
        
        res = self.http_client.get(
            "https://www.dhlottery.co.kr/login/selectRsaModulus.do",
            headers=headers
        )
        
        response_data = json.loads(res.text)
        return response_data.get("data", {})

    def _encrypt_with_rsa(self, plaintext: str, rsa_key_data: dict) -> str:
        """
        RSA 공개키로 텍스트 암호화
        
        Args:
            plaintext: 암호화할 평문
            rsa_key_data: {'rsaModulus': '...', 'publicExponent': '...'}
            
        Returns:
            str: 16진수로 인코딩된 암호문
        """
        modulus = int(rsa_key_data["rsaModulus"], 16)
        exponent = int(rsa_key_data["publicExponent"], 16)
        
        # RSA 공개키 생성
        rsa_key = RSA.construct((modulus, exponent))
        cipher = PKCS1_v1_5.new(rsa_key)
        
        # 암호화 및 16진수 변환
        encrypted_bytes = cipher.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.hex()

    def _get_j_session_id_from_session(self) -> str:
        """세션 쿠키에서 JSESSIONID 추출"""
        session_cookies = self.http_client.session.cookies
        
        for cookie in session_cookies:
            if cookie.name == "JSESSIONID":
                return cookie.value
        
        raise KeyError("JSESSIONID cookie is not set in session")

    def _get_j_session_id_from_response(self, res: requests.Response) -> str:
        """응답에서 JSESSIONID 추출 (레거시 호환성)"""
        assert type(res) == requests.Response

        for cookie in res.cookies:
            if cookie.name == "JSESSIONID":
                return cookie.value
        
        # 응답에 없으면 세션에서 시도
        return self._get_j_session_id_from_session()

    def _generate_req_headers(self, j_session_id: str) -> dict:
        assert type(j_session_id) == str

        copied_headers = copy.deepcopy(self._REQ_HEADERS)
        copied_headers["Cookie"] = f"JSESSIONID={j_session_id}"
        return copied_headers

    def _generate_body(self, user_id: str, encrypted_password: str) -> dict:
        """
        로그인 요청 본문 생성
        
        Args:
            user_id: 사용자 ID (평문)
            encrypted_password: RSA 암호화된 비밀번호
        """
        assert type(user_id) == str
        assert type(encrypted_password) == str

        return {
            "userId": user_id,
            "password": encrypted_password,
        }

    def _try_login(self, headers: dict, data: dict) -> dict:
        """
        새 로그인 API 호출
        
        Returns:
            dict: 로그인 응답 JSON
        """
        assert type(headers) == dict
        assert type(data) == dict

        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
        headers["X-Requested-With"] = "XMLHttpRequest"

        res = self.http_client.post(
            "https://www.dhlottery.co.kr/login/securityLoginCheck.do",
            headers=headers,
            data=data,
        )
        
        try:
            return json.loads(res.text)
        except json.JSONDecodeError:
            # HTML 응답인 경우 (리다이렉트 등)
            return {"result": "success" if res.status_code == 200 else "fail"}

    def _update_auth_cred(self, j_session_id: str) -> None:
        assert type(j_session_id) == str
        self._AUTH_CRED = j_session_id
    
    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        if not self._AUTH_CRED:
            return False
            
        headers = self.add_auth_cred_to_headers(self._REQ_HEADERS)
        res = self.http_client.get(
            "https://www.dhlottery.co.kr/userSsl.do?method=myPage",
            headers=headers
        )
        
        # 마이페이지에 접근 가능하면 로그인 상태
        return "로그인" not in res.text or "마이페이지" in res.text
