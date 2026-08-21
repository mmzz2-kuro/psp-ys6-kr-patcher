# 070. Ys VI 빈 한글 번역 필터 추가 결과

## 수행 내용

- 대화 편집기 상단 상태 필터와 별도로 `번역 비어 있음만` 체크박스를 추가했다.
- 체크박스는 `translation`을 정규화한 뒤 공백을 제거한 값이 비어 있는 레코드를
  표시한다.
- 검색어, 역할 및 상태 필터를 먼저 적용하고 빈 번역 조건을 이어서 적용하므로 모든
  필터를 교집합으로 조합해 사용할 수 있다.
- 빈 번역 판정을 별도 함수로 분리해 GUI를 실행하지 않고도 검증할 수 있게 했다.

## 변경 파일

- `tools/ys6_dialogue_viewer.py`
- `docs/plan/070-ys6-empty-korean-translation-filter.md`
- `docs/result/070-ys6-empty-korean-translation-filter.md`

## 검증 결과

- `python -m py_compile tools/ys6_dialogue_viewer.py`: 통과
- 빈 문자열, 공백 문자열, `translation` 키 누락 및 번역문 존재 표본 검증: 통과
- `untranslated`, `draft`, `override` 상태와 무관한 빈 번역 판정 표본 검증: 통과
- 체크박스와 `전체`, `dialogue`, `draft`, `override` 상태 필터 조합 검증: 통과
- 검색어 및 역할 필터와 체크박스 조합 검증: 통과
- 현재 `dialogue-translations.json` 집계:
  - 전체 7,424개
  - 빈 번역 2,255개
  - 현재 데이터에서는 빈 번역 2,255개가 모두 `untranslated`

## 보존 사항 및 알려진 문제

- 사용자가 수정 중인 `tools/config/dialogue-translations.json`은 변경하지 않았다.
- 번역 데이터, 상태 값, 패치 빌드 및 ISO에는 변경이 없다.
- 실제 GUI 화면 조작은 수행하지 않았으며 필터 함수와 Python 구문을 비GUI 방식으로
  검증했다.
- 생성한 임시 ROM은 없다.
