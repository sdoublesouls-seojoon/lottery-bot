"""
Selenium 기반 로또645 구매 자동화 모듈

기존 requests 방식의 세션 관리 문제를 해결하기 위해
Selenium 브라우저 자동화로 전환
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Chrome WebDriver 생성
    
    Args:
        headless: True면 화면 없이 실행 (GitHub Actions용)
    
    Returns:
        Chrome WebDriver 인스턴스
    """
    options = Options()
    
    if headless:
        options.add_argument("--headless=new")
    
    # 기본 설정
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # User-Agent 설정
    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    # WebDriver 생성
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # 암묵적 대기 설정
    driver.implicitly_wait(10)
    
    return driver


def login(driver: webdriver.Chrome, user_id: str, password: str) -> bool:
    """
    동행복권 로그인 (메인 페이지 경유)
    
    Args:
        driver: WebDriver 인스턴스
        user_id: 사용자 ID
        password: 비밀번호
    
    Returns:
        로그인 성공 여부
    """
    print("🏠 메인 페이지 접속 중...")
    driver.get("https://www.dhlottery.co.kr/main")
    
    time.sleep(2)  # 페이지 로딩 대기
    save_screenshot(driver, "01_main_page")
    
    try:
        # 로그인 버튼/링크 찾기 (메인 페이지에서)
        print("🔐 로그인 페이지로 이동 중...")
        login_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn_common.sml.blu, a[href*='login'], .header_login a"))
        )
        login_link.click()
        
        time.sleep(3)  # 로그인 페이지 로딩 대기
        save_screenshot(driver, "02_login_page")
        
        # ID 입력 - element_to_be_clickable로 대기
        print("ID 입력 필드 대기 중...")
        user_id_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "inpUserId"))
        )
        
        # JavaScript로 값 입력 (더 안정적)
        driver.execute_script("arguments[0].value = arguments[1]", user_id_input, user_id)
        print(f"✓ ID 입력 완료")
        
        # 비밀번호 입력
        print("비밀번호 입력 필드 대기 중...")
        password_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "inpUserPswdEncn"))
        )
        driver.execute_script("arguments[0].value = arguments[1]", password_input, password)
        print(f"✓ 비밀번호 입력 완료")
        
        # 스크린샷 저장
        save_screenshot(driver, "03_credentials_entered")
        
        # 로그인 버튼 클릭
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnLogin"))
        )
        login_btn.click()
        print("🔄 로그인 버튼 클릭...")
        
        # 로그인 완료 대기
        time.sleep(3)
        
        # 로그인 성공 확인
        current_url = driver.current_url.lower()
        page_source = driver.page_source
        
        # 마이페이지 링크가 있거나 로그인 페이지가 아니면 성공
        if "login" not in current_url or "마이페이지" in page_source or "로그아웃" in page_source:
            print("✓ 로그인 성공!")
            save_screenshot(driver, "04_login_success")
            return True
        else:
            print("❌ 로그인 실패 - 로그인 페이지에 머물러 있음")
            save_screenshot(driver, "04_login_failed")
            return False
            
    except TimeoutException:
        print("❌ 로그인 실패 - 요소 찾기 타임아웃")
        save_screenshot(driver, "error_login_timeout")
        return False
    except Exception as e:
        print(f"❌ 로그인 실패 - {e}")
        save_screenshot(driver, "error_login_exception")
        return False


def navigate_to_lotto645(driver: webdriver.Chrome) -> bool:
    """
    로또645 구매 페이지로 이동
    
    Args:
        driver: WebDriver 인스턴스
    
    Returns:
        이동 성공 여부
    """
    print("🎰 로또645 페이지로 이동 중...")
    
    try:
        # 로또645 구매 페이지 직접 접속
        driver.get("https://ol.dhlottery.co.kr/olotto/game/game645.do")
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        save_screenshot(driver, "05_lotto645_page")
        
        # 세션 만료 확인
        page_source = driver.page_source
        if "시간 초과" in page_source or "세션이 해제" in page_source:
            print("❌ 세션 만료됨!")
            return False
        
        # 판매 시간 외 팝업 확인 (alert 또는 div로 표시될 수 있음)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            print(f"ℹ️ 알림: {alert_text}")
            alert.accept()  # 확인 클릭
            save_screenshot(driver, "05_after_alert")
        except:
            pass  # 알림이 없으면 통과
        
        # 팝업 div 확인 (판매 시간 외 메시지)
        if "존재하지 않습니다" in page_source or "회차정보가 존재하지" in page_source:
            print("ℹ️ 현재 판매 시간이 아닙니다 (회차정보 없음)")
            save_screenshot(driver, "05_no_round_info")
            return True  # 정상 - 판매 시간이 아닐 뿐
        
        print("✓ 로또645 페이지 접속 성공!")
        return True
        
    except Exception as e:
        print(f"❌ 로또645 페이지 이동 실패 - {e}")
        save_screenshot(driver, "error_navigate_lotto645")
        return False


def open_purchase_popup(driver: webdriver.Chrome) -> bool:
    """
    로또 구매 팝업(또는 구매 영역) 오픈
    
    Args:
        driver: WebDriver 인스턴스
    
    Returns:
        성공 여부
    """
    print("🎫 구매 영역 확인 중...")
    
    try:
        # 먼저 팝업 div 확인 (판매 시간 외)
        page_source = driver.page_source
        
        # 확인 버튼이 있는 팝업 처리
        try:
            confirm_btn = driver.find_element(By.CSS_SELECTOR, ".btn_common, .popup_btn button, button.confirm")
            confirm_btn.click()
            print("ℹ️ 팝업 확인 버튼 클릭")
            time.sleep(1)
            save_screenshot(driver, "06_popup_confirmed")
        except:
            pass
        
        # 자동번호발급 버튼 확인 시도
        try:
            auto_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "num1"))
            )
            print("✓ 자동번호발급 버튼 발견!")
            
            # 클릭 시도 (게임이 없을 수 있음)
            try:
                auto_btn.click()
                print("✓ 자동번호발급 버튼 클릭!")
                time.sleep(1)
                save_screenshot(driver, "06_auto_btn_clicked")
            except Exception as e:
                print(f"⚠️ 버튼 클릭 불가: {e}")
                
        except TimeoutException:
            print("ℹ️ 자동번호발급 버튼 없음 (판매 시간 외)")
        
        # 현재 상태 확인
        page_source = driver.page_source
        
        if "현재 구매 가능한 복권이 없습니다" in page_source:
            print("ℹ️ 현재 구매 가능한 복권이 없습니다 (판매 시간 외)")
            save_screenshot(driver, "06_no_lottery_available")
            return True  # 정상 동작 - 판매 시간이 아닐 뿐
        
        if "존재하지 않습니다" in page_source or "회차정보" in page_source:
            print("ℹ️ 회차정보가 없습니다 (판매 시간 외)")
            return True  # 정상 - 판매 시간이 아닐 뿐
        
        print("✓ 구매 페이지 접근 완료")
        return True
        
    except Exception as e:
        print(f"❌ 구매 팝업 오픈 실패 - {e}")
        save_screenshot(driver, "error_purchase_popup")
        return False


def save_screenshot(driver: webdriver.Chrome, name: str) -> None:
    """스크린샷 저장"""
    try:
        # GitHub Actions 환경이면 workspace에 저장
        output_dir = os.getenv('GITHUB_WORKSPACE', '.')
        filepath = os.path.join(output_dir, f"screenshot_{name}.png")
        driver.save_screenshot(filepath)
        print(f"📸 스크린샷 저장: {filepath}")
    except Exception as e:
        print(f"⚠️ 스크린샷 저장 실패: {e}")


def run_selenium_buy(user_id: str, password: str, count: int = 1) -> dict:
    """
    Selenium으로 로또 구매 실행
    
    Args:
        user_id: 사용자 ID
        password: 비밀번호
        count: 구매 게임 수 (1-5)
    
    Returns:
        결과 딕셔너리
    """
    result = {"success": False, "message": ""}
    driver = None
    
    try:
        # 환경변수로 headless 모드 제어 (기본: headless)
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        
        print("=" * 50)
        print("🚀 Selenium 로또 구매 시작")
        print(f"   Headless 모드: {headless}")
        print("=" * 50)
        
        # WebDriver 생성
        driver = create_driver(headless=headless)
        
        # 1. 로그인
        if not login(driver, user_id, password):
            result["message"] = "로그인 실패"
            return result
        
        # 2. 로또645 페이지 이동
        if not navigate_to_lotto645(driver):
            result["message"] = "로또645 페이지 이동 실패"
            return result
        
        # 3. 구매 팝업 오픈 (1차 목표)
        if not open_purchase_popup(driver):
            result["message"] = "구매 영역 접근 실패"
            return result
        
        # TODO: 추후 실제 구매 로직 구현
        # buy_auto(driver, count)
        
        print("=" * 50)
        print("✅ 1차 목표 달성: 구매 페이지 접근 성공!")
        print("=" * 50)
        
        result["success"] = True
        result["message"] = "구매 페이지 접근 성공 (1차 목표)"
        
    except Exception as e:
        print(f"❌ 예외 발생: {e}")
        result["message"] = str(e)
        if driver:
            save_screenshot(driver, "error_exception")
    
    finally:
        if driver:
            # 마지막 스크린샷
            save_screenshot(driver, "99_final_state")
            driver.quit()
            print("🔚 브라우저 종료")
    
    return result


# 직접 실행 시 테스트
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    user_id = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    count = int(os.getenv("COUNT", "1"))
    
    if not user_id or not password:
        print("❌ 환경변수에 USERNAME, PASSWORD를 설정해주세요")
        print("   .env 파일에 다음 형식으로 설정:")
        print("   USERNAME=your_id")
        print("   PASSWORD=your_password")
        exit(1)
    
    # 로컬 테스트 시 headless=false로 브라우저 표시
    os.environ["HEADLESS"] = "false"
    
    result = run_selenium_buy(user_id, password, count)
    print(f"\n결과: {result}")
