# 106. Ys VI SPECIAL VERSION 안전 한글 폰트 및 1차 대사 이식 결과

상태: 완료 (사용자 실기 확인)

## 초반 IDM 대사 보완

- 기존판 `s_0551/s_0551.xso.z` index 35~45의 초반 대사가 SPECIAL VERSION에서 XSO가 아닌 `s_scene.idm`으로 이동한 것을 확인했다.
- 독립 파일 `PSP_GAME/USRDIR/data/idm/s_05/s_0551/s_scene.idm`과 `s_0551.bin` index 6의 런타임 복사본을 함께 패치했다.
- IDM 헤더 및 201개 가변 레코드, 총 214개 문자열을 파일 끝까지 파싱하고 무수정 왕복 구조를 확인했다.
- 초반 대사 원문 11개는 IDM에서 모두 한 위치에 고유하게 대응됐다.
- 기존 SPECIAL VERSION 매핑 322자는 보존하고 신규 한글 17자만 추가해 mapping revision 2, 총 339자로 갱신했다.
- 수정 IDM 크기는 9,199바이트이며 독립 파일과 아카이브 엔트리의 할당 공간은 각각 10,240바이트다.
- 재생성 ISO에서 두 IDM 복사본을 재추출한 결과 서로 및 작업본과 바이트 단위로 일치했다.
- 11개 번역의 인코딩 바이트를 다시 비교했으며 불일치가 없었다.

## 수행 내용

- SPECIAL VERSION 원본 ISO의 독립 XSO와 698개 정상 아카이브를 다시 스캔했다.
- 독립 파일과 아카이브를 합쳐 XSO 런타임 후보 3,458개를 카탈로그화했다.
- 100번에서 산출한 구조 대응 후보 1,169개 중 현재 상태가 `override`인 레코드를 대상으로 다시 검증했다.
- SPECIAL VERSION 대상 XSO의 문자열 인덱스와 일본어 원문 바이트가 모두 일치할 때만 번역을 이식했다.
- 16×14 전용 폰트 테이블 1,771개에서 전체 XSO 문자열 및 실행 파일 외부 사용과 충돌하지 않는 안전 슬롯을 계산했다.
- 105번의 `風`, `気` 임시 전역 치환은 제거하고 전용 안전 매핑만 적용했다.
- 수정 BOOT, 평문 EBOOT, 독립 XSO와 아카이브 복사본을 포함한 테스트 ISO를 생성했다.

## 이식 결과

- 구조 대응 후보: 1,169개
- 현재 `override`이면서 구조 후보인 레코드: 201개
- 원문·인덱스 재검증 통과: 190개
  - payload 완전 동일: 180개
  - 코드 구조·문자열 수 동일: 10개
- 원문 또는 인덱스 불일치 제외: 11개
- 수정 런타임 XSO: 34개
- 수정 아카이브: 18개
- 수정 독립 XSO: 8개
- 공유 payload 번역 충돌: 0개
- 할당 공간 초과: 0개

현재 번역 데이터에서 구조 후보가 아닌 5,087개 `override` 레코드는 계획의 제외 범위대로 건드리지 않았다. 100번의 1,169개는 모든 번역 상태를 포함한 구조 후보 수이고, 실제 패치는 그중 현재 `override`이며 원문까지 일치하는 항목만 사용했다.

## 폰트 결과

- SPECIAL VERSION 폰트 레코드: 1,771개
- 확인된 안전 슬롯: 434개
- 1차 이식에 필요한 고유 한글: 322개
- 남은 안전 슬롯: 112개
- 배정 코드 및 폰트 인덱스 중복: 0개
- 16×14 셀 초과 또는 공백 글리프: 0개
- 전용 매핑 revision: 1

## 주요 확인 대상

- `s_02/s_0202/talkoruha3.xso.z`: 오르하에게 거울 조각을 돌려주는 대화 35개
- `s_46/s_4611/startrelease.xso.z`: 해방 이벤트 관련 대화 32개
- `s_46/s_4611/talktera.xso.z`: 테라 대화 6개
- `s_70/s_7100/formov_battleboss.xso.z`: 보스전 관련 대화 6개
- 여러 맵의 `save.xso.z`: 저장 확인 메시지

## 생성·변경 파일

- 빌더: `tools/scripts/ys6_special_dialogue_port.py`
- SPECIAL VERSION 카탈로그: `tools/patchdata/work/current/106-special-version-first-dialogue-port/dialogue-catalog.json`
- 런타임 맵: `tools/patchdata/work/current/106-special-version-first-dialogue-port/runtime-map.json`
- 폰트 사용량 및 안전 슬롯: `tools/patchdata/work/current/106-special-version-first-dialogue-port/font-usage.json`
- 전용 매핑: `tools/patchdata/work/current/106-special-version-first-dialogue-port/hangul-mapping.json`
- 글리프 아틀라스: `tools/patchdata/work/current/106-special-version-first-dialogue-port/hangul-atlas.png`
- 이식 레코드: `tools/patchdata/work/current/106-special-version-first-dialogue-port/port-records.csv`
- 빌드 보고서: `tools/patchdata/work/current/106-special-version-first-dialogue-port/port-report.json`
- ISO 재추출 검증: `tools/patchdata/work/current/106-special-version-first-dialogue-port/iso-reextract-verification.json`
- 테스트 ISO: `patched/106-special-version-first-dialogue-port/Ys VI Special Version - 106-first-dialogue-port.iso`

## 검증 결과

- 원본 ISO SHA-256 검증: 통과
- BOOT 및 EBOOT 원본 SHA-256 검증: 통과
- Python 구문 검사: 통과
- XSO 재구성 및 컨테이너 왕복 검사: 통과
- 수정 런타임 XSO 34개 ISO 재추출 및 SHA-256 검사: 통과
- ISO 재추출 BOOT·EBOOT와 작업본 비교: 바이트 단위 일치
- 초반 IDM 201개 레코드·214개 문자열 재파싱: 통과
- 초반 IDM 번역 11개 인코딩 검증: 통과
- 독립 IDM과 아카이브 IDM 복사본 동일성: 통과
- ISO 허용 범위 밖 변경: 0건
- 테스트 ISO 크기: 711,917,568바이트
- 테스트 ISO SHA-256: `B36AF70925EF93E096F4F2453A06220587E01F68E5C19D53B8157DA517B5F8CD`
- 수정 BOOT SHA-256: `7B4532F5EF70D007A04C1FD2B02C82AB39188FBC8EA24702C59A806145E7FA64`
- 수정 EBOOT SHA-256: `B416115982CAEADB26B07A68C56121B3B56EDC7AABA2E3CB86EB415EADCB4DB2`
- 수정 IDM SHA-256: `1E150BC576C2D16EBBB84FE5D7E0CBDB936E14988AD1B79F34B163484890659B`

## 사용자 실기 확인 필요

1. 테스트 ISO가 정상 부팅되는지 확인한다.
2. 위 주요 확인 대상 중 접근 가능한 장면에서 한글 대사가 표시되는지 확인한다.
3. 글자의 높이, 기준선, 자간 및 잘림을 확인한다.
4. 번역하지 않은 일본어 문장에서 임의의 한자가 한글로 바뀌지 않았는지 확인한다.
5. 대화 종료, 저장 및 맵 전환이 정상 진행되는지 확인한다.

사용자가 SPECIAL VERSION 실기에서 초반 IDM 한글 대사가 정상 표시되는 것을 확인했다.

## 알려진 사항 및 정리 대상

- 이번 ISO는 SPECIAL VERSION 전체 패치가 아닌 안전 슬롯 및 1차 대사 이식 시험본이다.
- 자동 대응되지 않은 대사, 인물·몬스터명, 아이템, 시스템 메시지, 이미지, 영상과 XMB는 포함하지 않았다.
- 실제 기기 확인 전에는 106번을 최종 완료로 확정하지 않는다.
- 검증 완료 후 불필요하면 이번 테스트 ISO를 삭제할 수 있다.
