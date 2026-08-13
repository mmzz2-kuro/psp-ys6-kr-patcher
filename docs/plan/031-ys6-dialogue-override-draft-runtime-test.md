# Ys VI 대사 override·draft 인게임 역테스트 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- preflight: 완료
- ISO 생성: 완료
- 정적 역테스트: 완료
- 인게임 검증: 완료
- 결과 문서: `/docs/result/031-ys6-dialogue-override-draft-runtime-test.md`

## 목적

새 대사 작업 흐름에서 `override`만 패치에 적용되고 `draft`는 번역문이 있어도 일본어 원문으로 유지되는지 실제 게임에서 확인한다.

## 고정 테스트 조건

대상:

- 맵: `s_02 / s_020a`
- XSO: `adolsleep.xso.z`

상태:

| 인덱스 | 상태 | 기대 결과 |
|---|---|---|
| 29 | `override` | `오르하야, 부디 잊지 말거라.` 출력 |
| 30 | `override` | `정령신 알마의 후예인 무녀로서의 본분을.` 출력 |
| 31 | `override` | 한글 번역 출력 |
| 32 | `override` | 한글 번역 출력 |
| 33 | `draft` | 일본어 원문 출력 |

33번의 draft 번역문은 JSON에 보존하지만 빌드 대상, 글리프 수집 및 XSO 교체 내용에는 포함하지 않는다.

## 누적 적용 범위

- 대사 override: 142개
- `adolsleep` 29~32 신규 승인 포함
- 인물명 reviewed: 14개
- 대사 draft: 19개, 모두 제외

현재 작업공간의 모든 override를 누적 적용하므로, 029 이후 사용자가 승인한 다른 대사도 함께 포함된다.

## 처리 절차

1. 작업공간 SHA와 상태 수 고정
2. override 142개만 선택되는지 검증
3. `adolsleep` 인덱스 29~32가 교체 목록에 있고 33이 없는지 XSO 재파싱 확인
4. 글리프·아카이브 할당 preflight
5. 원본 ISO에서 031 전용 ISO 생성
6. 허용 extent 밖 변경 여부 확인
7. PPSSPP 인게임 역테스트

## 원본 및 출력

- 원본 ISO는 읽기 전용으로 유지한다.
- 기존 029 ISO를 덮어쓰지 않는다.
- 작업 경로: `/.work/ys6-dialogue-override-draft-runtime-test`
- 출력 ISO: `/patched/031-dialogue-override-draft-runtime-test/Ys VI - dialogue-override-draft-test.iso`

## 정적 검증

- 전체 작업공간 유효
- override 정확히 142개
- draft 정확히 19개
- `adolsleep` 29~32 교체 성공
- `adolsleep` 33 원본 raw bytes 유지
- 일본어 ruby 제거 승인 필드 유지
- 인물명 14개 유지
- 아카이브 할당 초과 없음
- 허용 ISO 범위 밖 변경 없음
- 원본 ISO SHA 유지
- 자동 테스트 및 Python 컴파일 통과

## 인게임 확인

`adolsleep` 이벤트에서 다음 순서로 확인한다.

1. 29~32번이 한글로 출력됨
2. 33번 `……とにかく今は / ゆっくりお休みになってください。`는 일본어로 출력됨
3. 대사창 진행과 이벤트 종료 정상
4. 한글 글자 깨짐·잘림 없음

## 완료 조건

- override와 draft가 실제 게임에서 기대대로 분리된다.
- draft 번역은 JSON에 보존된 채 패치에는 포함되지 않는다.
- 결과 문서에 정적·인게임 결과를 기록한다.

## 중단 조건

- 빌드 전 override/draft 수 또는 29~33 상태 변경
- 인덱스 33이 교체 데이터에 포함됨
- 원문 SHA 불일치
- 아카이브 용량 초과
- 허용 범위 밖 ISO 변경
