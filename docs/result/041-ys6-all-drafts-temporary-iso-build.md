# 041. 전체 draft 임시 override 테스트 ISO 빌드 결과

## 결과

현재 draft 4,628개를 임시 복사본에서 override로 승격하는 작업과 작업공간 검증은 성공했다. 그러나 전체 통합 preflight가 `ridepedestal` many-to-many 런타임 매핑에서 중단되어 ISO는 생성하지 않았다.

계획에서 정한 대로 문제 항목을 임의 제외하거나 공유 payload의 번역을 임의 선택하지 않았다.

## 임시 승격 결과

- 원본 작업공간 SHA-256: `67D7193C34159BAD6E978C9A63AF0406328C2346CF8295FAF85C02411496BAB8`
- 임시 승격본 SHA-256: `FD1BA27033AF7D4773A96CB8E74012C7F7C77E0C87DAD319DC90B90531344A53`
- 임시 override: 4,628개
- 작업공간 검증 오류: 0개
- 원본 작업공간의 상태는 변경하지 않음

## 첫 번째 빌드 차단 원인

- XSO SHA-256: `14A9CE5A99110527DDF4BEEF2A597EA46EC83F942E9CA1212712D218CB8B1772`
- 런타임 매핑 상태: `many_to_many`
- 대상 XSO: `ridepedestal`
- 독립 경로 3개와 아카이브 내부 런타임 경로 3개가 연결됨

대상 경로:

- `s_10/s_1009/ridepedestal.xso.z`
- `s_10/s_1010/ridepedestal.xso.z`
- `s_70/s_7101/ridepedestal.xso.z`

각 경로의 번역은 현재 동일하다.

- 인덱스 0: `예`
- 인덱스 2: `아니오`

따라서 기술적으로는 동일 payload를 재구축한 뒤 세 런타임 아카이브와 세 독립 경로에 같은 결과를 쓰는 지원을 빌더에 추가할 수 있다. 현재 빌더에는 이 동작이 구현되어 있지 않다.

## 전체 빌드 가능성 분석

전체 임시 승격본을 런타임 매핑과 공유 payload 기준으로 추가 분석한 결과:

- 전체 override: 4,628개
- many-to-many 때문에 제외되는 레코드: 28개
- 공유 payload 번역 충돌: 68그룹, 138개 레코드
- 현재 빌더로 안전하게 선택 가능한 부분집합: 4,462개

공유 payload 충돌은 같은 실제 XSO 데이터와 같은 문자열 인덱스에 서로 다른 번역이 지정된 경우다. 하나를 임의 선택하면 다른 맵의 의도된 번역이 사라질 수 있으므로 자동 선택하지 않았다.

## 생성 파일

- `/.work/ys6-all-drafts-test-build/dialogue-translations.override.json`
- `/.work/ys6-all-drafts-test-build/risk-all.json`
- `/.work/ys6-all-drafts-test-build/valid.json`
- `/.work/ys6-all-drafts-test-build/buildable.json`

## 다음 선택지

### 1. 안전 부분집합 ISO 생성

- 4,462개 번역만 포함한다.
- 166개는 테스트 ISO에서 제외된다.
- 가장 빠르게 게임 전반의 번역 상태를 확인할 수 있다.

### 2. 전체 적용 문제를 먼저 해결

- 빌더에 동일 번역 many-to-many 지원을 추가한다.
- 공유 payload 충돌 68그룹을 검토하여 번역을 통일하거나 런타임별 분리 방식을 설계한다.
- 해결 후 4,628개 전체 preflight와 ISO 빌드를 다시 수행한다.

## 권장

이번 목적이 우선 전체적인 게임 화면 확인이라면 4,462개 안전 부분집합 ISO를 먼저 만드는 것이 실용적이다. 제외 목록은 유지되므로 이후 166개를 해결한 완전판과 비교할 수 있다.

## ROM 처리

- 원본 ISO는 수정하지 않았다.
- 패치 ISO는 생성하지 않았다.
- 기존 `/patched` 파일은 변경하지 않았다.
- 현재 삭제할 새 임시 ROM은 없다.
