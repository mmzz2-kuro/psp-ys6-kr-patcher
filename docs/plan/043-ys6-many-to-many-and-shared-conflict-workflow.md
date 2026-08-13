# 043. many-to-many 빌더 지원 및 공유 payload conflict 전환 계획

## 목적

테스트 ISO에서 제외된 166개를 두 단계로 처리한다.

1. 번역 충돌이 없는 many-to-many 28개를 빌더가 모든 연결 대상에 적용할 수 있도록 확장한다.
2. 공유 payload 번역 충돌 138개를 GUI에서 쉽게 검토하도록 `conflict` 상태로 변경한다.

## 현재 대상

### many-to-many 28개

2개 XSO payload, 5개 독립 경로에 걸친 28개 레코드다.

- `14A9CE5A...`: `ridepedestal`, 3개 경로, 번역 레코드 6개
- `BBB88381...`: `talkgasshu`, 2개 경로, 번역 레코드 22개

구현 전 동일 payload의 동일 문자열 인덱스별 번역이 모든 경로에서 완전히 같은지 다시 검사한다. 하나라도 다르면 many-to-many 자동 적용 대상에서 제외하고 공유 충돌로 분류한다.

### 공유 payload 충돌 138개

- XSO payload: 18개
- 충돌 그룹: 68개
- 레코드: 138개

현재 작업공간을 기준으로 다시 계산하며, 계획 042의 오래된 목록만 그대로 적용하지 않는다.

## 1단계: many-to-many 빌더 지원

### 그룹 모델 변경

현재 통합 빌더는 XSO 그룹마다 다음을 하나씩만 보관한다.

- `runtime_key` 1개
- 대표 런타임 아카이브 1개

이를 다음 구조로 확장한다.

- `runtime_keys`: 연결된 런타임 대상 전체
- `standalone_paths`: 연결된 독립 XSO 전체
- 동일 payload는 한 번만 재구축·압축
- 재구축한 동일 컨테이너를 모든 런타임 아카이브 엔트리와 독립 XSO에 적용

### 안전 조건

- 매핑 상태가 `many_to_many`여도 동일 인덱스의 번역이 모든 원본 경로에서 같을 때만 허용한다.
- 각 런타임 엔트리의 원본 payload SHA-256이 그룹 해시와 같아야 한다.
- 모든 엔트리의 할당 공간을 개별 검사한다.
- 하나라도 공간이 부족하면 그룹 전체를 실패 처리한다.
- 독립 경로도 각각 원본 payload와 ISO 할당 공간을 검사한다.
- 같은 아카이브 안에 여러 엔트리가 있으면 최신 수정본을 기준으로 순차 교체한다.

### 보고서 변경

- XSO 보고서에 연결 런타임 키 전체와 대상 수를 기록한다.
- 아카이브 보고서의 수정 XSO 수를 실제 교체 엔트리 수로 계산한다.
- standalone 보고서에 모든 독립 경로를 기록한다.
- build manifest가 many-to-many 대상과 적용 수를 명시한다.

## 2단계: 공유 payload 충돌 138개 표시

### 상태 변경

- 현재도 공유 payload의 동일 인덱스에 서로 다른 번역이 있는 레코드만 찾는다.
- 해당 레코드를 `draft`에서 `conflict`로 변경한다.
- notes에 `shared-payload review 043`을 추가한다.
- 번역문, 원문, 해시와 기존 허용 메타데이터는 변경하지 않는다.
- 변경 전 작업공간을 `/.work/ys6-shared-payload-review`에 백업한다.

### 사용자 검토 후 동작

- GUI에서 상태 필터를 `conflict`로 선택한다.
- 같은 payload·인덱스 후보를 동일한 번역으로 통일한다.
- 통일한 항목은 `draft`로 되돌린다.
- 후속 검사에서 모든 관련 경로의 번역이 같아졌는지 확인한다.

현재 GUI는 단일 레코드만 보여 주므로 notes에 그룹 식별자(`XSO SHA-256 앞자리 + 인덱스`)도 기록하여 같은 그룹을 검색할 수 있게 한다. 필요하면 후속 작업에서 GUI에 그룹 후보 비교 기능을 추가한다.

## 구현 파일

- `/tools/scripts/ys6_integrated_build.py`
- `/tools/scripts/ys6_all_drafts_risk.py` 또는 공유 충돌 전용 스크립트
- `/tools/config/dialogue-translations.json`
- 관련 테스트 및 보고서

## 작업 절차

1. 현재 작업공간 SHA-256과 상태 수를 기록한다.
2. many-to-many 28개를 payload·인덱스별로 재검사한다.
3. 통합 빌더의 그룹 구조와 다중 런타임 교체를 구현한다.
4. 28개만 포함한 최소 작업공간으로 preflight를 실행한다.
5. 아카이브 5개 경로와 독립 XSO 5개 경로의 적용 및 round-trip을 검증한다.
6. 전체 임시 override에서 many-to-many 28개가 더 이상 제외되지 않는지 검사한다.
7. 현재 공유 payload 충돌을 다시 계산한다.
8. 정확히 일치하는 대상만 `conflict`로 전환한다.
9. GUI의 `conflict` 필터 노출을 확인한다.
10. 원본 작업공간 검증과 상태 수를 확인한다.
11. 결과 문서를 작성한다.

## 완료 기준

- many-to-many 동일 번역 그룹이 통합 빌더 preflight를 통과한다.
- 동일 재구축 payload가 연결된 모든 런타임 엔트리와 독립 경로에 적용된다.
- 각 대상의 원본 해시와 공간 검사가 유지된다.
- 공유 payload 충돌 대상만 `conflict`가 된다.
- 예상치 138개와 달라지면 실제 재계산 결과와 이유를 보고한다.
- 원본 ISO와 기존 패치 ISO는 변경하지 않는다.
- 이번 단계에서는 새 ISO를 만들지 않는다. 전체 충돌 통일 후 완전판 ISO를 별도로 생성한다.

## 복구

- 상태 변경 전 작업공간 백업을 보존한다.
- 빌더 변경은 기존 one-to-one 및 standalone 매핑의 동작을 유지하도록 회귀 preflight로 확인한다.
- 상태 표시가 잘못되면 백업에서 작업공간을 복원할 수 있다.

## 상태

- 계획 확인 완료
- many-to-many 빌더 지원 및 회귀 preflight 완료
- 공유 payload 충돌 68그룹·138개 conflict 전환 완료
- 결과 문서: `/docs/result/043-ys6-many-to-many-and-shared-conflict-workflow.md`
