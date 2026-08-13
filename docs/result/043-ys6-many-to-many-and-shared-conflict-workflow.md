# 043. many-to-many 빌더 지원 및 공유 payload conflict 전환 결과

## 결과

번역 충돌이 없는 many-to-many 28개를 통합 빌더에서 안전하게 처리할 수 있도록 확장했다. 공유 payload의 동일 문자열 인덱스에 서로 다른 번역이 지정된 68그룹·138개는 사용자가 GUI에서 통일할 수 있도록 `conflict` 상태로 변경했다.

이번 작업에서는 ISO를 생성하거나 수정하지 않았다.

## many-to-many 지원

### 대상

- XSO payload: 2개
- 번역 레코드: 28개
- 런타임 아카이브 엔트리: 5개
- 독립 XSO 경로: 5개

대상 payload:

- `14A9CE5A99110527DDF4BEEF2A597EA46EC83F942E9CA1212712D218CB8B1772`
  - `ridepedestal`
  - 독립 경로 3개, 런타임 아카이브 3개
- `BBB883819E82D28FA569CA8A04D72A60B927160AF7F79B7618F2872D8F75F4D5`
  - `talkgasshu`
  - 독립 경로 2개, 런타임 아카이브 2개

### 구현

- 동일 payload는 한 번만 재구축하고 압축한다.
- 재구축 결과를 연결된 모든 런타임 아카이브 엔트리에 적용한다.
- 연결된 모든 독립 XSO에도 같은 결과를 적용한다.
- 모든 런타임 및 독립 대상의 원본 payload 해시를 각각 확인한다.
- 모든 대상의 할당 공간을 각각 확인한다.
- 동일 payload·인덱스에 서로 다른 번역이 있으면 기존과 같이 빌드를 차단한다.

## preflight 검증

### 28개 최소 검증

- override: 28개
- XSO payload: 2개
- 아카이브: 5개
- 독립 XSO: 5개
- 공간 초과: 0개
- 결과: 통과

### 전체 회귀 검증

공유 충돌 138개를 제외한 현재 draft 4,490개를 임시 override로 승격했다.

- override: 4,490개
- XSO payload: 448개
- 아카이브: 49개
- 독립 XSO: 422개
- 인물명: 14개
- 글리프: 939개
- 공간 초과: 0개
- 결과: 통과

## 공유 payload conflict 전환

- 충돌 그룹: 68개
- conflict 레코드: 138개
- 나머지 draft: 4,490개
- override: 0개
- notes 표식: `shared-payload review 043 {해시 앞 12자리}#{인덱스}`
- 작업공간 검증: 통과

변경 전 작업공간:

- SHA-256: `67D7193C34159BAD6E978C9A63AF0406328C2346CF8295FAF85C02411496BAB8`
- 백업: `/.work/ys6-shared-payload-review/dialogue-translations.before.json`

변경 후 작업공간:

- SHA-256: `7BB26462C54BD3800D49C313ECAD9FDFC7AFEF8B5872BF89435C4280886F1166`
- 변경 보고서: `/.work/ys6-shared-payload-review/mark-report.json`

## GUI 검토 방법

1. 대사 GUI에서 상태 필터를 `conflict`로 선택한다.
2. 한 항목을 선택하고 notes의 그룹 식별자를 확인한다.
3. 검색창에 그룹 식별자 예: `ABCDEF123456#7`을 입력하면 같은 충돌 그룹만 표시된다.
4. 표시된 모든 번역을 공통으로 사용할 한 문장으로 통일한다.
5. 통일이 끝난 항목의 상태를 `draft`로 되돌린다.

GUI 검색 대상에 notes를 추가했으므로 그룹 식별자 검색이 가능하다.

## 변경 파일

- `/tools/scripts/ys6_integrated_build.py`
- `/tools/scripts/ys6_all_drafts_risk.py`
- `/tools/scripts/ys6_mark_shared_payload_conflicts.py`
- `/tools/ys6_dialogue_viewer.py`
- `/tools/config/dialogue-translations.json`
- `/docs/plan/043-ys6-many-to-many-and-shared-conflict-workflow.md`
- `/docs/result/043-ys6-many-to-many-and-shared-conflict-workflow.md`

## 다음 단계

- 사용자가 conflict 68그룹의 번역을 통일한다.
- 통일 후 공유 payload 충돌 검사를 다시 실행한다.
- 충돌이 0개가 되면 전체 draft 4,628개를 임시 override로 승격한다.
- 전체 preflight와 완전판 테스트 ISO 빌드를 수행한다.

## ROM 처리

- 원본 ISO를 변경하지 않았다.
- 기존 패치 ISO를 변경하지 않았다.
- 새 ISO를 생성하지 않았다.
