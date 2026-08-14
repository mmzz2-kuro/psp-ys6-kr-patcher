# 045. 전체 draft 4,628개 정식 override 전환 계획

## 목적

전체 대사 테스트 ISO에 사용한 draft 4,628개를 원본 번역 작업공간에서 정식 `override` 상태로 전환한다. 이후 GUI 및 패치 빌더가 별도의 임시 작업공간 없이 전체 번역을 패치 대상으로 사용하게 한다.

## 사용자 판단

- 전체 반영 지점을 플레이로 확인하려면 시간이 많이 필요하므로 현재 테스트 ISO의 성공적인 빌드와 확인된 한글 출력 결과를 기준으로 우선 정식 승격한다.
- 전체 게임 플레이 검증은 완료되지 않았으며, 이후 문제 발견 시 개별 항목을 다시 `draft` 또는 `conflict`로 내릴 수 있다.

## 대상

- 작업공간: `/tools/config/dialogue-translations.json`
- 현재 상태:
  - 전체 레코드: 7,424개
  - draft: 4,628개
  - conflict: 0개
  - override: 0개
- 승격 후 예상 상태:
  - draft: 0개
  - conflict: 0개
  - override: 4,628개

번역이 없는 `untranslated`, `excluded`, `orphaned` 레코드는 변경하지 않는다.

## 안전 조건

- 번역문이 존재하는 `draft`만 승격한다.
- 번역문, 원문, source SHA-256, notes 및 허용 메타데이터는 변경하지 않는다.
- 승격 전에 현재 작업공간과 044 빌드에 사용한 임시 override 작업공간을 키별로 비교한다.
- 두 작업공간의 번역문 또는 메타데이터가 다르면 상태 변경 전에 중단한다.
- 변경 전 전체 작업공간을 `/.work/ys6-promote-overrides-045`에 백업한다.

## 작업 절차

1. 현재 작업공간 SHA-256과 상태별 수량을 기록한다.
2. 044 임시 승격본 `/.work/ys6-many-to-many-043/recheck-all-4628.json`과 현재 작업공간을 비교한다.
3. 대상 키 4,628개의 번역, 원문 해시, notes 및 허용 메타데이터 일치를 확인한다.
4. 현재 작업공간 전체 백업을 생성한다.
5. 번역이 있는 draft 4,628개를 override로 변경한다.
6. 작업공간 검증을 실행한다.
7. 공유 payload 충돌이 0개인지 다시 검사한다.
8. 통합 preflight를 실행하여 정식 작업공간만으로 4,628개 빌드가 가능한지 확인한다.
9. 상태 수와 SHA-256을 기록한다.
10. 결과 문서를 작성한다.

## 검증 기준

- 정확히 4,628개만 상태가 변경되어야 한다.
- 번역문과 메타데이터 변경 수는 0개여야 한다.
- override 4,628개, draft 0개, conflict 0개여야 한다.
- 작업공간 검증 오류가 0개여야 한다.
- 공유 payload 충돌이 0개여야 한다.
- 정식 작업공간을 사용한 통합 preflight가 통과해야 한다.
- 원본 ISO 및 기존 패치 ISO는 수정하지 않는다.

## 복구

- 변경 전 백업: `/.work/ys6-promote-overrides-045/dialogue-translations.before.json`
- 문제가 발견되면 개별 레코드를 `draft` 또는 `conflict`로 되돌릴 수 있다.
- 전체 전환을 취소해야 하면 백업 파일로 복구할 수 있다.

## 결과물

- 갱신된 `/tools/config/dialogue-translations.json`
- 승격 스크립트 또는 승격 보고서
- `/docs/result/045-ys6-promote-all-drafts-to-override.md`

## ROM 처리

- 이번 작업에서는 ISO를 생성하거나 수정하지 않는다.
- 044 테스트 ISO는 그대로 보존한다.

## 상태

- 계획 확인 완료
- 전체 draft 4,628개 정식 override 전환 완료
- 정식 작업공간 preflight 완료
- 결과 문서: `/docs/result/045-ys6-promote-all-drafts-to-override.md`
