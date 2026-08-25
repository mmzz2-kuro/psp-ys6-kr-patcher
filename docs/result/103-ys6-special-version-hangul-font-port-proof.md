# 103. Ys VI SPECIAL VERSION 한글 폰트 이식 검증 결과

상태: 완료

## 결론

- `ULJM-05155 SPECIAL VERSION`에도 내장 비트맵 폰트가 있으며 한글 글리프를 삽입할 수 있다.
- 기존 ULJM-05009와 폰트 규격이 달라 기존 고정 오프셋 패처를 그대로 사용할 수는 없지만, 버전별 프로필을 분리하면 공통 렌더링 방식을 확장할 수 있다.
- 일시정지 메뉴의 `再開`을 `한글`로 표시하도록 만든 최소 시험 ELF와 테스트 ISO를 생성했다.
- ISO 구조, 할당 공간, 변경 범위와 재추출 파일은 모두 검증됐다.
- 현재 환경에는 PPSSPP 실행 파일이 없어 실제 게임 화면 출력 여부는 사용자 테스트가 필요하다.

## 확인된 SPECIAL VERSION 폰트 구조

| 항목 | ULJM-05009 | ULJM-05155 SPECIAL VERSION |
|---|---:|---:|
| 테이블 시작 | `0x13E88C` | `0x15EB2A` |
| 글리프 셀 | 16×12 | 16×14 |
| 레코드 크기 | 26바이트 | 30바이트 |
| 확인된 글리프 수 | 4,608 | 1,771 |

- SPECIAL VERSION 테이블은 코드 2바이트와 16×14 1bpp 비트맵 28바이트로 구성된다.
- 시작부 코드 `0x8140`, `0x8141`, `0x8142`, `0x8143`이 30바이트 간격으로 연속되는 고유 시그니처를 확인했다.
- 시험에는 실행 파일의 다른 문자열에서 사용되지 않는 `0xE5E5`, `0xE978` 슬롯을 사용했다.

## 최소 출력 시험

- 대상 문자열: 일시정지 메뉴의 `再開`
- 문자열 위치: `0x147B58`
- 시험 표시 문구: `한글`
- 인코딩: `E5 E5 E9 78`
- `한`: 폰트 인덱스 1,758, 비트맵 위치 `0x16B930`
- `글`: 폰트 인덱스 1,769, 비트맵 위치 `0x16BA7A`
- 수정 ELF 크기: 2,070,916바이트
- 수정 ELF SHA-256: `4221247343210AA702BD942B824F162A5326FF0A701F7904C02BDC0DD10FEBC2`
- 실제 변경 바이트: 55바이트

글리프 코드 자체와 렌더링 코드는 변경하지 않았다. 선택한 기존 코드의 비트맵과 시험 문자열 네 바이트만 변경했다.

## EBOOT 적용 방식

- SPECIAL VERSION의 `BOOT.BIN`은 분석 및 수정 가능한 평문 ELF이다.
- 기존 ULJM-05009 패치 방식과 동일하게 평문 ELF를 실행용 `EBOOT.BIN` 위치에도 배치했다.
- 원본 암호화 EBOOT 크기를 유지하기 위해 ELF 뒤의 원본 꼬리 348바이트를 보존했다.
- 출력 EBOOT 크기: 2,071,264바이트
- 출력 EBOOT SHA-256: `8CB0181B7D471027064BFD533343024A18C57387C5D43AA757E61DCB219FE0E5`
- 출력 EBOOT는 `7F 45 4C 46`으로 시작하는 ELF이며 원래 ISO 할당 공간 2,072,576바이트 안에 들어간다.

## 생성 파일

- 테스트 ISO: `patched/103-special-version-font-test/Ys VI Special Version - 103-hangul-font-test.iso`
- 전용 분석·생성 스크립트: `tools/scripts/ys6_special_font_proof.py`
- 수정 BOOT: `tools/patchdata/work/current/103-special-version-font-port/BOOT-font-proof.bin`
- 수정 EBOOT: `tools/patchdata/work/current/103-special-version-font-port/EBOOT-font-proof.bin`
- 글리프 미리보기: `tools/patchdata/work/current/103-special-version-font-port/hangul-proof-atlas.png`
- 검증 보고서: `tools/patchdata/work/current/103-special-version-font-port/report.json`

## ISO 검증

- 원본 SPECIAL VERSION ISO SHA-256: `C7BFF86BB7AA9DE025B4717BE34516A3E52D88EF8AD9AA3696F048D4ECCAE1A9`
- 테스트 ISO 크기: 711,917,568바이트
- 테스트 ISO SHA-256: `A22E74DB4E5ECCED6689FACAC8CB08ED43674B54EEB629030EFF26B853452489`
- 교체 파일: `BOOT.BIN`, `EBOOT.BIN` 2개
- ISO 허용 범위 밖 변경: 0건
- ISO에서 재추출한 BOOT와 작업 BOOT: 바이트 단위 일치
- ISO에서 재추출한 EBOOT와 작업 EBOOT: 바이트 단위 일치
- 두 실행 파일의 ELF 헤더: 정상
- Python 문법 검사와 생성 스크립트 내부 검증: 통과

## 사용자 테스트 방법

1. 테스트 ISO를 PPSSPP 또는 PSP CFW 환경에서 실행한다.
2. 게임을 시작해 일시정지 메뉴를 연다.
3. 기존 `再開` 위치가 `한글`로 표시되는지 확인한다.
4. 두 글자가 16×14 셀 안에서 잘리지 않는지 확인한다.
5. 일시정지 메뉴 복귀와 게임 진행이 정상인지 확인한다.

## 알려진 사항

- 글리프 미리보기에서는 `한글` 형태와 16×14 셀 경계를 확인했다.
- 실제 화면의 자간, 기준선과 색상은 게임 실행 결과로 최종 확인해야 한다.
- 시험 슬롯은 실행 파일 내 비폰트 영역에서 사용되지 않음을 확인했지만, 전체 SPECIAL VERSION 대사 이식 단계에서는 모든 XSO 사용량을 다시 집계해 대규모 안전 슬롯 목록을 만들어야 한다.
- PPSSPP에서 평문 ELF EBOOT가 실행되더라도 정식 펌웨어 실기에서는 CFW 환경이나 별도 실행 파일 처리가 필요할 수 있다.
- 이번 ISO는 폰트 가능성 검증용이며 완성 한글패치가 아니다.

## 후속 권장 작업

- 실제 화면에서 최소 한글 출력이 확인되면 SPECIAL VERSION 전체 폰트 사용량과 안전 슬롯을 새로 산출한다.
- 이어서 새 XSO 카탈로그·런타임 맵을 만들고 100번 조사에서 확인한 구조 대응 1,169개 번역 레코드를 우선 이식한다.
- SPECIAL VERSION 정식 빌드 프로필과 GUI 통합은 대사 출력 검증 이후 진행한다.

## 정리 대상

- 원본 ISO는 변경하지 않았다.
- 별도의 임시 테스트 ISO는 만들지 않았으며 보관 대상 테스트 ISO 한 개만 생성했다.
