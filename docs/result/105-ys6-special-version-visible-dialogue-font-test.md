# 105. Ys VI SPECIAL VERSION 확인용 대사 한글 글리프 테스트 결과

상태: 완료

## 수행 내용

- 사용자가 제시한 이샤 대사에서 바로 확인할 수 있도록 SPECIAL VERSION 내장 폰트의 두 한자 비트맵을 한글로 교체했다.
  - `風` (`0x9597`) → `한`
  - `気` (`0x8B43`) → `글`
- 외부 XSO와 원문 대사 데이터는 변경하지 않았다.
- 화면에서는 `風がざわめいた気がして……` 부분이 `한がざわめいた글がして……`처럼 표시되어야 한다.
- 103번 생성기에 `--visible-dialogue` 시험 모드를 추가했다.

## 변경 위치

| 원문 | 시험 글자 | 코드 | 인덱스 | 비트맵 위치 |
|---|---|---:|---:|---:|
| `風` | `한` | `0x9597` | 1,493 | `0x169A22` |
| `気` | `글` | `0x8B43` | 554 | `0x162C18` |

- 글리프 코드는 변경하지 않았다.
- 두 28바이트 비트맵 영역 안에서 실제로 달라진 바이트는 총 51바이트다.
- 실행 코드와 문자열 데이터에는 변경이 없다.

## 생성 파일

- 테스트 ISO: `patched/105-special-version-visible-font-test/Ys VI Special Version - 105-visible-hangul-font-test.iso`
- 생성 스크립트: `tools/scripts/ys6_special_font_proof.py`
- 수정 BOOT: `tools/patchdata/work/current/105-special-version-visible-font-test/BOOT-font-proof.bin`
- 수정 EBOOT: `tools/patchdata/work/current/105-special-version-visible-font-test/EBOOT-font-proof.bin`
- 글리프 미리보기: `tools/patchdata/work/current/105-special-version-visible-font-test/hangul-proof-atlas.png`
- 보고서: `tools/patchdata/work/current/105-special-version-visible-font-test/report.json`

## 검증 결과

- Python 문법 검사: 통과
- 입력 SPECIAL VERSION ISO, BOOT와 EBOOT SHA-256 검증: 통과
- 폰트 테이블 시그니처와 두 한자 코드 위치 검증: 통과
- 글리프 미리보기: `한글` 모두 16×14 셀 안에 표시
- 변경 범위: 두 글리프 비트맵 영역으로 제한
- 수정 BOOT 크기: 2,070,916바이트
- 수정 BOOT SHA-256: `F7046AC3D8F5AE4EE830D113AB337217FD9AA3FBA1541F8190C434FCB27E6DAB`
- 수정 EBOOT 크기: 2,071,264바이트
- 수정 EBOOT SHA-256: `6156C21D440F1B14C067B9A26C59193D80E24C8A646F59913F3A520ECAB0DB3A`
- 원본 EBOOT 꼬리 348바이트 보존
- ISO에서 재추출한 BOOT와 EBOOT: 작업본과 바이트 단위 일치
- ISO 허용 범위 밖 변경: 0건
- 테스트 ISO 크기: 711,917,568바이트
- 테스트 ISO SHA-256: `F13E0BB717027C78C7005BA32052C491C0E76DA88962E6F587393C0599E5CF67`

## 사용자 확인 방법

1. 105번 테스트 ISO로 게임을 실행한다.
2. 사용자가 제시한 이샤 대사 장면으로 이동한다.
3. `風` 자리에 `한`, `気` 자리에 `글`이 보이는지 확인한다.
4. 글자의 높이, 기준선, 잘림과 자간을 확인한다.

## 알려진 사항

- `風`과 `気`의 폰트 비트맵을 전역 교체했으므로 테스트 ISO의 다른 일본어 문장에서도 두 한자가 각각 `한`, `글`로 보일 수 있다.
- 이는 실제 한글패치 매핑이 아니라 폰트 렌더링 경로를 확인하기 위한 임시 시험이다.
- 실제 게임 출력 확인 전까지 SPECIAL VERSION 정식 폰트 이식 성공으로 확정하지 않는다.
- 103번 테스트 ISO와 원본 SPECIAL VERSION ISO는 변경하지 않았다.

## 정리 대상

- 별도 출력으로 생성된 105번 테스트 ISO는 검증 완료 후 필요하지 않으면 삭제할 수 있다.
