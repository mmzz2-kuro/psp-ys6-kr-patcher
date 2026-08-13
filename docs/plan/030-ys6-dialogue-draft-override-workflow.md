# Ys VI 대사 초벌 번역·override 승인 작업 흐름 전환 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- 상태 체계 구현: 완료
- 기존 번역 이관: 완료
- 첫 dialogue 번역: 완료(18개)
- GUI 자동·정적 검증: 완료
- 사용자 GUI 검토: 대기
- 패치 적용 검증: preflight 완료
- 결과 문서: `/docs/result/030-ys6-dialogue-draft-override-workflow.md`

## 요청 흐름

대사 번역은 다음 3단계로 관리한다.

1. Codex가 일본어 `dialogue` 원문을 한글로 초벌 번역한다.
2. 사용자가 GUI에서 번역을 읽고 교정하거나 승인하여 `override`로 전환한다.
3. 통합 빌더는 `override` 대사만 한글 패치에 적용한다.

초벌 번역은 사용자의 승인 없이 ISO에 들어가지 않아야 한다.

## 현재 상태

- 전체 카탈로그 문자열: 7,424개
- `dialogue` 역할: 4,754개
- dialogue 포함 XSO 경로: 509개
- 현재 누적 번역: 115개
  - dialogue: 74개
  - choice 등 기타: 41개 이상
  - 현재 상태는 모두 `reviewed`

인물명 작업공간은 이번 변경 대상이 아니다. `/tools/config/cast-names.json`은 기존 `reviewed` 체계를 유지한다.

## 상태 체계

대사 작업공간 상태를 다음과 같이 정의한다.

- `untranslated`: 번역 없음
- `draft`: Codex 초벌 번역 또는 사용자 검토 중
- `override`: 사용자가 승인했으며 패치에 적용할 번역
- `excluded`: 번역 및 적용 제외
- `conflict`: 원문 또는 원문 SHA 변경
- `orphaned`: 새 카탈로그에서 사라진 항목

기존 `reviewed`는 대사 작업공간에서 deprecated 상태로 취급하고, 현재 115개는 내용 변경 없이 `override`로 일괄 이관한다.

## 적용 규칙

- 통합 빌더는 대사 상태가 `override`인 항목만 선택한다.
- `draft`는 번역이 있어도 글리프 생성과 ISO 패치에서 제외한다.
- `override`는 번역 비어 있음, NUL, 제어 토큰 불일치, 허용되지 않은 마크업 변경을 오류로 처리한다.
- 기존 115개 이관 전후에 레코드 내용과 순서를 비교하며 `status` 이외 변경이 없어야 한다.
- 인물명은 계속 `reviewed`만 적용한다.

## 대사 작업공간 확장

현재 `/tools/config/dialogue-translations.json`은 적용된 115개만 들어 있다. 초벌 번역 대상을 관리하기 위해 전체 카탈로그 7,424개와 동기화한다.

동기화 규칙:

- 기존 115개는 번역·메모·허용 마크업 설정을 보존하고 `override`로 이관
- 신규 카탈로그 항목은 `untranslated`
- 원문 SHA가 바뀐 기존 항목은 `conflict`
- 사라진 항목은 `orphaned`
- 동일 `(iso_path, string_index)` 중복은 오류

GUI 성능을 확인하고, 기본 화면은 전체 7,424개가 아닌 `dialogue` 역할 중심으로 필터링할 수 있게 한다.

## GUI 변경

기존 대사 탭을 새 작업 흐름에 맞춘다.

- 상태 목록에 `override` 추가
- 기존 `reviewed` 신규 선택은 제거 또는 deprecated 표시
- 상태 필터 추가:
  - 전체
  - dialogue
  - 초벌 번역(`draft`)
  - 적용 승인(`override`)
  - 미번역(`untranslated`)
- 목록에 상태 열 추가
- `draft → override`를 쉽게 전환
- 저장 전 전체 작업공간 검증
- 저장은 기존 원자적 교체 및 `.bak` 백업 유지
- 검색과 역할 필터 유지

GUI에서 `draft`와 `override`가 시각적으로 명확히 구분되어야 한다.

## Codex 번역 원칙

첫 단계에서는 `roles`에 `dialogue`가 포함된 항목만 번역한다.

- 선택지(`choice`)는 후속 별도 묶음
- 화자명(`speaker`)은 `cast-names.json` 관리
- 리소스명과 미참조 문자열 제외
- 제어 코드와 마크업을 정확히 보존
- 앞뒤 대사, 맵, XSO, 문자열 순서를 함께 읽어 문맥 반영
- 고유명사는 이미 확정된 인물명 표기를 우선 사용
- 번역문은 모두 `draft`
- 자동으로 `override`로 지정하지 않음
- 직역이 불확실하거나 화자·상황이 모호하면 메모에 표시

## 첫 번역 묶음

작업 흐름을 검증하기 위해 전체 4,754개를 한 번에 번역하지 않는다. 첫 묶음은 게임 초반 진행과 현재 접근 가능한 범위를 우선한다.

선정 방식:

1. `s_02`와 `s_05` 계열 맵의 `dialogue`
2. 기존 override 74개 dialogue는 제외
3. 아직 번역이 없는 연속 이벤트·대화 단위 선택
4. 동일 XSO의 문맥을 끊지 않는 범위
5. 첫 묶음 상한은 약 100개

실제 대상 경로와 개수는 구현 시 카탈로그에서 산출해 번역 보고서에 기록한다. 100개를 넘는 하나의 이벤트는 중간에서 자르지 않고 다음 묶음으로 넘긴다.

## 구현 대상

- 수정: `/tools/scripts/ys6_translation_workspace.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정 또는 추가: `/tools/scripts/tests`
- 수정: `/tools/config/dialogue-translations.json`
- 생성: 첫 dialogue 초벌 번역 보고서

필요하면 `/tools/scripts`에 대사 묶음 선정·검증 스크립트를 추가한다. GUI 없는 Python 스크립트로 작성한다.

## 검증

### 상태 및 데이터

- 전체 작업공간 7,424개와 카탈로그 키 일치
- 기존 번역 115개가 모두 `override`
- 기존 115개에서 `status` 외 내용 변경 0건
- 첫 초벌 번역은 모두 `draft`
- draft가 ISO 적용 대상에서 제외됨
- override만 통합 빌더에 선택됨
- 인물명 reviewed 처리 회귀 없음

### 번역

- 첫 묶음이 모두 `dialogue` 역할
- 제어 토큰과 마크업 보존
- 빈 번역 없음
- 동일 XSO 내 문맥 검토
- 고유명사 표기 일관성 확인

### GUI

- 7,424개 자동 로드 성능 확인
- dialogue·draft·override·untranslated 필터 동작
- draft 교정 후 override 전환 및 저장
- 재실행 시 상태 유지
- CSV 왕복 시 override 상태 유지

### 빌드

- 상태 전환 직후에는 새 ISO를 만들지 않고 preflight로만 확인
- 기존 115개 override만 선택했을 때 029 이전 대사 적용 결과 유지
- draft를 override로 바꾼 뒤 후속 빌드에서만 새 대사가 포함됨

## 원본 및 ROM 보호

- 원본 ISO와 기존 029 ISO를 수정하지 않는다.
- 030에서는 상태 체계와 첫 초벌 번역을 준비하며 새 최종 ISO를 만들지 않는다.
- 사용자가 초벌 번역을 교정하고 override로 전환한 다음 별도 계획에서 ISO를 생성한다.
- 변경 전 `/tools/config/dialogue-translations.json`을 별도 백업한다.

## 결과 산출물

- 전체 대사 작업공간: `/tools/config/dialogue-translations.json`
- 자동 백업: `/tools/config/dialogue-translations.json.bak`
- 첫 번역 묶음 보고서: `/.work/ys6-dialogue-draft-override/`
- 결과 문서: `/docs/result/030-ys6-dialogue-draft-override-workflow.md`

## 완료 조건

- 대사 상태 흐름이 `draft → override → 패치 적용`으로 동작한다.
- 기존 115개가 안전하게 override로 이관된다.
- 전체 카탈로그가 GUI 작업공간에 동기화된다.
- 첫 초반 dialogue 묶음을 Codex가 번역해 draft로 저장한다.
- 사용자가 GUI에서 draft를 검토하고 override로 바꿀 수 있다.
- draft는 패치에 절대 포함되지 않는다.
- 자동 테스트와 컴파일이 통과한다.
- 결과 문서가 작성된다.

## 중단 및 재확인 조건

- 기존 115개 번역에서 status 이외 내용이 변경됨
- 전체 동기화 후 키 중복 또는 원문 SHA 충돌 발생
- `reviewed`를 사용하는 기존 인물명 흐름에 영향 발생
- GUI가 7,424개 작업공간을 실용적으로 처리하지 못함
- 첫 번역 묶음의 문맥을 카탈로그만으로 안전하게 판단할 수 없음
- 토큰 또는 마크업을 보존할 수 없는 항목 발견
