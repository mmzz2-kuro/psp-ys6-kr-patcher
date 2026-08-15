# 052. Ys VI 확장 EUC-JP 시스템 메시지 추출 및 작업공간 병합 결과

## 결과

기존 추출기가 제외하던 내부 줄바꿈 포함 EUC-JP 문자열과 짧은 메뉴 문자열을 안전한 널 종료 저장 단위로 다시 추출했다. 기존 260개 레코드를 그대로 보존하고 확정된 신규 레코드 58개를 `untranslated` 상태로 병합했다.

- 병합 전: 260개
- 신규 확정: 58개
- 병합 후: 318개
- 수동 검토 후보: 18개

초기 조사에서 확인한 155개는 줄 단위 탐색 결과였다. 실제 EBOOT에서는 여러 줄이 `0A`로 연결되고 마지막에만 `00`으로 종료되므로, 안전하게 패치할 수 있는 실제 저장 단위는 58개다.

## 신규 확정 항목

### 짧은 메뉴·상태 문자열 6개

- `戻る`: `0x11E4B8`
- `アドル`: `0x11EC28`
- `再開`: `0x11F1C4`
- `戻る`: `0x120DF4`
- `攻撃`: `0x120DFC`
- `＜毒＞`: `0x121648`

### 저장·불러오기 메시지 23개

범위: `0x1223E8`~`0x122D78`

다음과 같은 메시지가 여러 줄을 포함한 하나의 레코드로 등록됐다.

- 데이터 로드·저장·삭제 진행 안내
- 메모리스틱 분리 및 전원 차단 경고
- 저장 공간 부족
- 메모리스틱 미삽입·분리·접근 오류
- 손상된 데이터·데이터 없음·내부 오류
- UMD 미삽입 및 종류 오류
- 타이틀 복귀와 확인 선택지

`%lu`가 포함된 레코드는 `format_tokens`에 해당 토큰을 기록했다.

### 검·마법·강화 메시지 29개

범위: `0x12DCB4`~`0x12E864`

- 메일스트롬·익스플로전·라이트닝 단계별 정보
- 윈드·플레임·선더 검 기술
- 마력 게이지 자동 상승
- 검 마법 위력 강화
- 검의 예리함 및 기술 해금 안내

중복 원문도 실제 저장 오프셋이 다르면 별도 레코드로 유지했다.

## 구현 내용

`/tools/scripts/ys6_system_message_workspace.py`를 확장했다.

- 내부 `CR`, `LF`, `TAB`을 허용하는 EUC-JP 널 종료 레코드 추출
- EBOOT 데이터 영역의 2~3자 짧은 일본어 레코드 탐색
- 확정 범위와 명시적인 짧은 문자열 오프셋만 자동 병합
- 기존 레코드와 신규 레코드를 오프셋 순으로 병합
- 기존 레코드의 번역·상태·분류·메모 보존
- `%lu` 등 printf 형식 토큰 추출 및 override 번역 보존 검사
- 병합 전 JSON 자동 백업
- 확정·후보 CSV/JSON 및 병합 요약 생성

## 기존 데이터 보존 검증

병합 전 260개와 병합 결과의 같은 식별자를 전체 JSON 레코드 단위로 비교했다.

```text
preserved_exactly: true
changed existing records: 0
```

따라서 사용자가 작성한 기존 번역, override/draft/conflict 상태, 분류 및 메모는 변경되지 않았다.

## 역테스트 및 단위검증

### 형식 토큰

원문에 `%lu`가 있는 신규 레코드를 `%lu` 없는 override 번역으로 변경한 역테스트에서 `format token mismatch` 오류가 발생하는 것을 확인했다.

### 다중 행 패치

`SYS_001223E8`을 메모리상 다음 3행 한글로 임시 패치했다.

```text
데이터를 불러옵니다.
메모리 스틱을 빼거나
전원을 끄지 마세요.
```

- 할당 공간: 99바이트
- 인코딩 및 종료 길이: 69바이트
- 레코드 바로 다음 바이트 보존: 확인
- 기본 JSON의 해당 항목은 번역하지 않았으며 `untranslated` 상태 유지

## 전체 검증

- Python 구문 검사: 통과
- `git diff --check`: 오류 없음
- 패치 데이터 검사: 통과
- 전체 ISO preflight: 통과

```text
valid: true
dialogue override: 4665
xso: 463
archives: 49
standalone: 450
cast names: 58
items: 72
system messages applied: 49
glyphs: 971
overflow: 0
```

신규 58개는 모두 `untranslated`이므로 현재 적용 수 49에는 포함되지 않는다.

## 분석 산출물

`/.work/ys6-extended-system-messages/`:

- `confirmed-new.json`
- `confirmed-new.csv`
- `candidate-review.json`
- `candidate-review.csv`
- `merge-summary.json`
- `merged-system-messages.json`

18개 수동 검토 후보는 실행 코드가 우연히 EUC-JP로 해석된 형태가 대부분이므로 기본 작업공간에서 제외했다.

## 변경 파일

- `/tools/scripts/ys6_system_message_workspace.py`
- `/tools/config/system-messages.json`
- `/docs/plan/052-ys6-extended-euc-system-message-extraction.md`
- `/docs/result/052-ys6-extended-euc-system-message-extraction.md`

## ROM 처리

- 원본 ISO와 원본 EBOOT는 수정하지 않았다.
- 새 ISO를 생성하지 않았다.
- preflight 산출물만 `/tools/patchdata/work/current`에 갱신했다.
