# 109. Ys VI SPECIAL VERSION IDM 전체 대사 카탈로그 및 번역 이식 결과

상태: 테스트 ISO 생성 완료 / 사용자 실기 확인 대기

## 수행 내용

- SPECIAL VERSION의 `s_scene.idm` 241개를 전부 조사했다.
- 106번 IDM 파서·재구성기를 `ys6_idm.py` 공용 모듈로 분리했다.
- 0바이트 빈 IDM 64개와 인자 수가 큰 구조 변형 1개를 포함해 241개 모두 파싱 또는 정상 빈 파일로 분류했다.
- 모든 비어 있지 않은 IDM을 무수정 재구성해 원본과 바이트 단위로 비교했다.
- 독립 IDM과 `s_*.bin` 내부 런타임 복사본 관계를 카탈로그화했다.
- 기존 `override` 번역을 같은 맵의 raw 원문 및 앞뒤 문맥으로 대응했다.
- 안전 대응 결과를 SPECIAL VERSION 전용 IDM 작업공간으로 생성했다.
- 106번 ISO와 mapping revision 2를 기준으로 신규 글리프 95자와 IDM 번역 1,650개를 증분 적용했다.

## 전체 IDM 조사 결과

- IDM 파일: 241개
- 파싱 실패: 0개
- 전체 레코드: 3,641개
- 전체 문자열: 6,341개
- 확인된 아카이브 런타임 복사본: 177개
- 기존 번역 안전 대응: 4,127개
- 원문 중복 또는 문맥 모호: 282개
- 원문 미대응: 665개
- 서로 다른 번역 충돌: 7개

충돌 7개는 `s_0202`의 같은 SPECIAL VERSION 문자열에 기존판의 서로 다른 번역 두 개가 대응된 경우다. 임의 선택하지 않고 이번 적용에서 제외했다.

## 글리프 용량 결과

- 106번 기존 매핑: revision 2, 339자
- 전체 안전 대응 번역에 필요한 신규 한글: 607자
- 남아 있던 안전 슬롯: 95개
- 109번 신규 배정: 95자
- 109번 최종 매핑: revision 3, 434자
- 안전 슬롯 범위에서 선택된 IDM 번역: 1,650개
- 글리프 용량 때문에 보류된 안전 대응 번역: 2,477개

기존 339개 문자 배정은 변경하지 않았으며, 신규 95자만 append-only로 추가했다. 전체 4,127개를 적용하려면 SPECIAL VERSION 폰트 확장이 필요하다.

## 2차 ISO 적용 결과

- 적용 IDM 번역: 1,650개
- 수정 독립 IDM: 88개
- 수정 아카이브 런타임 복사본: 88개
- 신규 글리프: 95개
- ISO 교체 대상: 178개
- IDM 또는 아카이브 할당 공간 초과: 0개
- 수정 허용 범위 밖 ISO 변경: 0개

109번 ISO는 검증된 106번 ISO를 기준 작업본으로 사용했다. 따라서 106번의 XSO 번역 190개, 초반 IDM 11개와 기존 글리프 339개를 유지하면서 109번 IDM 번역을 증분 적용한다.

## 검증 결과

- Python 구문 검사: 통과
- IDM 241개 구조 분류: 통과
- 비어 있지 않은 IDM 무수정 왕복: 통과
- ISO 재추출 IDM 번역 1,650개 인코딩 비교: 불일치 0개
- 수정 독립 IDM 88개 재파싱: 통과
- 아카이브 런타임 복사본 88개와 독립 IDM 비교: 불일치 0개
- 106번 기존 글리프 339개 비트맵 비교: 불일치 0개
- 최종 매핑 수: 434개
- 테스트 ISO SHA-256: `B610AF62DCFC476DD27D57ACDC0201B3E5E96DE166ED9722EC5F74D8E447B092`

## 생성·변경 파일

- `tools/scripts/ys6_idm.py`
- `tools/scripts/ys6_special_idm_catalog.py`
- `tools/scripts/ys6_special_idm_apply.py`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/idm-catalog.json`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/runtime-map.json`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/idm-translations.json`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/resolution-report.json`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/hangul-mapping.json`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/added-glyph-atlas.png`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/build-report.json`
- `tools/patchdata/work/current/109-special-version-idm-dialogue-port/iso-reextract-verification.json`
- `patched/109-special-version-idm-dialogue-port/Ys VI Special Version - 109-idm-dialogue-port.iso`

## 사용자 실기 확인 항목

1. 106번에서 확인한 첫 이샤·올하 장면이 계속 정상 출력되는지 확인한다.
2. 레다 마을과 초반 탐색 중 여러 NPC 대사가 한글로 표시되는지 확인한다.
3. 대화 종료, 맵 이동, 저장 및 전투 진입이 정상인지 확인한다.
4. 번역되지 않은 일본어 문자의 글리프가 한글로 바뀌지 않았는지 확인한다.
5. 한글 잘림, 기준선 또는 자간 문제가 새 글자에서도 없는지 확인한다.

## 알려진 문제 및 후속 과제

- 안전 대응 번역 2,477개는 글리프 슬롯 부족으로 보류됐다.
- 모호한 대응 282개, 미대응 665개와 충돌 7개는 별도 검토가 필요하다.
- 다음 전체 이식 단계에서는 1,771개 고정 폰트 테이블의 확장 또는 별도 한글 글리프 저장 영역 및 검색 코드 수정이 필요하다.
- 이번 테스트 ISO는 106번 테스트 ISO를 기준으로 생성했다. 원본 SPECIAL VERSION ISO와 106번 ISO는 변경하지 않았다.
