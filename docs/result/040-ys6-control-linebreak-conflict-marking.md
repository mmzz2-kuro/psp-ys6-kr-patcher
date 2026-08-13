# 040. 제어문자 불일치 항목 conflict 표시 결과

## 결과

사용자가 먼저 수정한 항목을 반영하여 현재 작업공간을 다시 검사했다. 기존 검토 대상 40개 중 11개는 해결되었고, 실제 제어문자 불일치가 남은 29개만 `draft`에서 `conflict`로 변경했다.

## 수행 내용

- 상태 변경 전 실제 검증기로 전체 draft 가상 승격 검사
- 잔여 제어문자 불일치 29개 확정
- 해당 레코드의 상태만 `conflict`로 변경
- notes에 `control-linebreak review 040` 추가
- 번역문, 원문, 해시 및 기존 허용 메타데이터는 유지
- 반복 가능한 비GUI 스크립트 추가

## 변경 파일

- `/tools/config/dialogue-translations.json`
- `/tools/scripts/ys6_mark_control_conflicts.py`
- `/docs/plan/040-ys6-control-linebreak-review.md`
- `/docs/result/040-ys6-control-linebreak-conflict-marking.md`

## 검증 결과

- 전체 레코드: 7,424개
- `draft`: 4,599개
- `conflict`: 29개
- `override`: 0개
- `control-linebreak review 040` 표시: 29개
- 작업공간 구조 검증: 통과
- GUI 상태 필터에 `conflict`가 포함된 것을 확인
- GUI 편집 상태 목록에 `conflict`가 포함된 것을 확인

## 해시 및 백업

- 변경 전 SHA-256: `53B65FEF4D3B764AD06C976FC25352364C8FC723D1FC3B2471CB97EAADD6B9AD`
- 변경 후 SHA-256: `B0D7211CCDE74FF0BF97917EB158036F230D723098ECA0124BF639D159FEDF96`
- 변경 전 백업: `/.work/ys6-control-conflict-review/dialogue-translations.before.json`
- 변경 보고서: `/.work/ys6-control-conflict-review/mark-report.json`

## 사용 방법

1. GUI 상태 필터에서 `conflict`를 선택한다.
2. 번역과 줄바꿈을 수정한다.
3. 검토 중이면 상태를 `draft`, 확정하여 패치에 넣으려면 `override`로 바꾼다.
4. `override`는 제어문자 검증을 통과해야 패치 빌드에 사용할 수 있다.

## ROM 처리

- 원본 및 패치 ISO를 수정하지 않았다.
- 새 테스트 ROM을 생성하지 않았다.
- 삭제할 임시 ROM은 없다.
