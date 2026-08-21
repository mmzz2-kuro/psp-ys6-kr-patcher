# 071. Ys VI 시스템 메시지 선택 상태 되돌림 수정 결과

## 수행 내용

- 시스템 메시지에서 `선택 항목 override` 실행 전에 현재 상세 편집값을 반영한다.
- 대상 레코드들을 변경한 뒤 첫 번째 선택 항목의 식별자로 목록 선택을 복원한다.
- 선택 복원 전에 이전 `_selected_identifier`를 초기화해 변경 전 상세 편집값이 다음
  선택 시 이전 레코드에 다시 저장되지 않게 했다.
- 상태 필터로 대표 항목이 목록에서 사라지면 내부 선택 식별자와 상세 편집창을 모두
  초기화한다.
- 다중 선택, 빈 번역 제외 및 길이 초과 `conflict` 판정은 유지했다.

## 변경 파일

- `tools/ys6_dialogue_viewer.py`
- `docs/plan/071-ys6-system-message-selection-state-fix.md`
- `docs/result/071-ys6-system-message-selection-state-fix.md`

## 검증 결과

- `python -m py_compile tools/ys6_dialogue_viewer.py`: 통과
- 시스템 메시지 작업공간 전체 318개 검증: 오류 0개
- `git diff --check`: 공백 오류 없음
- override 후 선택 복원 경로와 필터에서 항목이 사라질 때의 상세 초기화 경로를
  코드 수준에서 확인했다.

## 보존 사항 및 알려진 문제

- `tools/config/system-messages.json`은 이번 수정에서 변경하지 않았다.
- 대사·인물명·아이템 편집기 및 패치 빌드 로직은 변경하지 않았다.
- 실제 GUI 자동 조작 환경은 사용하지 않았으며 구문, 작업공간 검증 및 상태 전이
  경로를 비GUI 방식으로 확인했다.
- 생성하거나 수정한 ROM은 없다.
