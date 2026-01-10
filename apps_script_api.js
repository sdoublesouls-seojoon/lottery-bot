/**
 * 동행복권 수동 번호 구매용 Web App API
 * 
 * 배포 방법:
 * 1. Apps Script 에디터에서 이 코드 추가
 * 2. 배포 > 새 배포
 * 3. 유형: 웹 앱
 * 4. 실행 주체: 나
 * 5. 액세스 권한: 모든 사용자
 * 6. 배포 후 URL 복사하여 .env의 SHEET_API_URL에 설정
 */

function doGet(e) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("추첨번호");
    
    if (!sheet) {
      return createJsonResponse({ 
        success: false, 
        error: "시트 '추첨번호'를 찾을 수 없습니다" 
      });
    }
    
    // C2:H6 범위에서 5게임 x 6번호 가져오기
    const data = sheet.getRange("C2:H6").getValues();
    
    const games = data.map((row, index) => {
      // 빈 값 제외하고 숫자로 변환
      const numbers = row
        .filter(n => n !== "" && n !== null)
        .map(n => parseInt(n))
        .filter(n => !isNaN(n) && n >= 1 && n <= 45);
      
      return {
        game: index + 1,
        numbers: numbers
      };
    }).filter(game => game.numbers.length === 6); // 6개 번호가 있는 게임만
    
    return createJsonResponse({
      success: true,
      count: games.length,
      games: games
    });
    
  } catch (error) {
    return createJsonResponse({
      success: false,
      error: error.message
    });
  }
}

function createJsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 테스트 함수 - 스크립트 에디터에서 실행하여 확인
 */
function testGetNumbers() {
  const result = doGet({});
  const content = result.getContent();
  Logger.log(content);
}
