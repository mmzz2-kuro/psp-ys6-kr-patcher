# 045. 전체 draft 4,628개 정식 override 전환 결과

## 결과

전체 대사 draft 4,628개를 정식 `override`로 전환했다. 번역문과 원문 정보, 메모 및 허용 메타데이터는 변경하지 않았다. 이후 GUI와 패치 빌더는 별도의 임시 승격본 없이 정식 작업공간에서 전체 번역을 사용한다.

## 사전 대조

현재 작업공간과 044 ISO 빌드에 사용한 임시 override 작업공간을 키별로 비교했다.

- 현재 draft: 4,628개
- 임시 override: 4,628개
- 비교 필드: 번역, 원문 SHA-256, notes, `allow_markup_change`, `allow_player_name_expansion`
- 차이: 0개

## 상태 변경

- 승격 수: 4,628개
- 비상태 필드 변경: 0개
- 변경 전:
  - draft: 4,628개
  - override: 0개
  - conflict: 0개
- 변경 후:
  - draft: 0개
  - override: 4,628개
  - conflict: 0개
  - untranslated: 2,796개

## 검증 결과

- 작업공간 검증 오류: 0개
- 공유 payload 충돌: 0그룹, 0개
- 정식 작업공간 통합 preflight: 통과
- 대사 override: 4,628개
- XSO payload: 460개
- 아카이브: 49개
- 독립 XSO: 448개
- 공간 초과: 0개

preflight 시 현재 인물명 작업공간의 검수 완료 항목 58개가 함께 선택되었으며 전체 글리프 수는 948개였다. 인물명 작업공간은 이번 작업에서 변경하지 않았다.

## 해시와 백업

- 변경 전 SHA-256: `2C318B22401DFD56015BE1AE175AB0865CCA102F19FD7DEC40E71DB3A7D405F2`
- 변경 후 SHA-256: `45A528264ED9CAA8928D24691BDB4B44B1E2E89505B5D09F9584AC6CA20E3B63`
- 변경 전 백업: `/.work/ys6-promote-overrides-045/dialogue-translations.before.json`
- 승격 보고서: `/.work/ys6-promote-overrides-045/promotion-report.json`
- preflight: `/.work/ys6-promote-overrides-045/preflight`

변경 후 SHA-256은 044 빌드에 사용한 임시 override 작업공간과 동일하다.

## 변경 파일

- `/tools/config/dialogue-translations.json`
- `/tools/scripts/ys6_promote_all_drafts.py`
- `/tools/scripts/ys6_mark_shared_payload_conflicts.py`
- `/docs/plan/045-ys6-promote-all-drafts-to-override.md`
- `/docs/result/045-ys6-promote-all-drafts-to-override.md`

## 향후 수정 방법

- 실제 플레이 중 문제가 발견되면 해당 레코드를 `draft`로 내려 교정한다.
- 공유 payload 후보가 다시 달라지면 관련 그룹을 `conflict`로 표시한다.
- 교정 완료 후 `override`로 되돌리고 preflight를 다시 실행한다.

## 알려진 제한

- 전체 게임 플레이 검증은 완료되지 않았다.
- 화면 폭, 문맥 및 이벤트 진행 문제는 실제 플레이 중 추가로 발견될 수 있다.

## ROM 처리

- 이번 작업에서 ISO를 생성하거나 수정하지 않았다.
- 044 테스트 ISO와 기존 패치 ISO는 그대로 보존했다.
