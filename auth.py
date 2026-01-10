import copy
import json
import requests
from jsbn import RSAKey
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
        
        # Step 3: 사용자 ID와 비밀번호 RSA 암호화 (수정.md 참고: 둘 다 암호화 필요)
        encrypted_user_id = self._encrypt_with_rsa(user_id, rsa_key_data)
        encrypted_password = self._encrypt_with_rsa(password, rsa_key_data)
        
        # Step 4: 로그인 요청
        headers = self._generate_req_headers(default_auth_cred)
        data = self._generate_body(encrypted_user_id, encrypted_password)
        
        login_result = self._try_login(headers, data)

        # 디버깅: 로그인 응답 출력
        print(f"Login response: {login_result}")

        # Step 5: 로그인 성공 여부 확인 및 세션 저장
        if login_result.get("result") == "success" or login_result.get("loginYn") == "Y":
            # 로그인 후 새로운 세션 ID 획득 (중요!)
            logged_in_session_id = self._get_j_session_id_from_session()
            print(f"Session ID after login: {logged_in_session_id[:20]}...")

            self._update_auth_cred(logged_in_session_id)

            # Step 6: 다른 서브도메인(ol, el)에서도 세션 초기화
            self._initialize_subdomain_sessions(logged_in_session_id)

            print("✓ Login successful and session initialized")
            return True
        else:
            print(f"Login failed: {login_result.get('message', 'Unknown error')}")
            return False

    def add_auth_cred_to_headers(self, headers: dict) -> dict:
        assert type(headers) == dict

        copied_headers = copy.deepcopy(headers)
        copied_headers["Cookie"] = f"DHJSESSIONID={self._AUTH_CRED}"
        return copied_headers

    def _get_default_auth_cred(self) -> str:
        """로그인 페이지 접속으로 초기 세션 쿠키 획득"""
        # 로그인 페이지에 접속하여 세션 초기화
        self.http_client.get(
            "https://www.dhlottery.co.kr/user.do?method=login"
        )
        
        # 세션 쿠키에서 DHJSESSIONID 추출
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
        RSA 공개키로 텍스트 암호화 (jsbn 호환)
        
        Args:
            plaintext: 암호화할 평문
            rsa_key_data: {'rsaModulus': '...', 'publicExponent': '...'}
            
        Returns:
            str: 16진수로 인코딩된 암호문
        """
        modulus = rsa_key_data["rsaModulus"]
        exponent = rsa_key_data["publicExponent"]
        
        # pyjsbn-rsa로 RSA 공개키 설정 및 암호화
        rsa = RSAKey()
        rsa.setPublic(modulus, exponent)
        encrypted_hex = rsa.encrypt(plaintext)
        
        return encrypted_hex

    def _get_j_session_id_from_session(self) -> str:
        """세션 쿠키에서 DHJSESSIONID 추출"""
        session_cookies = self.http_client.session.cookies
        
        for cookie in session_cookies:
            if cookie.name == "DHJSESSIONID":
                return cookie.value
        
        raise KeyError("DHJSESSIONID cookie is not set in session")

    def _get_j_session_id_from_response(self, res: requests.Response) -> str:
        """응답에서 DHJSESSIONID 추출 (레거시 호환성)"""
        assert type(res) == requests.Response

        for cookie in res.cookies:
            if cookie.name == "DHJSESSIONID":
                return cookie.value
        
        # 응답에 없으면 세션에서 시도
        return self._get_j_session_id_from_session()

    def _generate_req_headers(self, j_session_id: str) -> dict:
        assert type(j_session_id) == str

        copied_headers = copy.deepcopy(self._REQ_HEADERS)
        copied_headers["Cookie"] = f"DHJSESSIONID={j_session_id}"
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

        # 세션 쿠키를 모든 서브도메인에서 사용할 수 있도록 설정
        from http.cookiejar import Cookie
        import time

        # .dhlottery.co.kr 도메인으로 쿠키 생성 (모든 서브도메인에서 사용 가능)
        cookie = Cookie(
            version=0,
            name='DHJSESSIONID',
            value=j_session_id,
            port=None,
            port_specified=False,
            domain='.dhlottery.co.kr',
            domain_specified=True,
            domain_initial_dot=True,
            path='/',
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False
        )

        # 세션 쿠키 jar에 추가
        self.http_client.session.cookies.set_cookie(cookie)
        print(f"✓ Session cookie set for .dhlottery.co.kr domain")
    
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

    def _initialize_subdomain_sessions(self, j_session_id: str) -> None:
        """
        로그인 후 다른 서브도메인(ol, el)에서도 세션 초기화

        Args:
            j_session_id: 로그인 세션 ID
        """
        headers = self._generate_req_headers(j_session_id)

        try:
            # el.dhlottery.co.kr 세션 초기화 (TotalGame.jsp)
            print("Initializing session for el.dhlottery.co.kr...")
            self.http_client.get(
                "https://el.dhlottery.co.kr/game/TotalGame.jsp?LottoId=LO40",
                headers=headers
            )
            print("✓ el.dhlottery.co.kr session initialized")

            # ol.dhlottery.co.kr 세션 초기화 (egovUserReadySocket.json으로 세션 활성화)
            print("Initializing session for ol.dhlottery.co.kr...")
            headers_ol = headers.copy()
            headers_ol["Referer"] = "https://ol.dhlottery.co.kr/olotto/game/game645.do"
            headers_ol["Content-Type"] = "application/json; charset=UTF-8"
            headers_ol["X-Requested-With"] = "XMLHttpRequest"

            self.http_client.post(
                "https://ol.dhlottery.co.kr/olotto/game/egovUserReadySocket.json",
                headers=headers_ol
            )
            print("✓ ol.dhlottery.co.kr session initialized")

        except Exception as e:
            print(f"Warning: Failed to initialize subdomain sessions: {e}")
