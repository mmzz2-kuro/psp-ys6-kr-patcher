# Ys VI `.z` 재압축 라운드트립 결과

## 상태

- 완료
- 사용자 승인: 2026-08-11

## 결론

Ys VI `.z` 컨테이너 생성 및 재압축 기능을 구현했다. 실제 표본 32개를 해제 후 zlib 레벨 9로 다시 압축한 결과, payload뿐 아니라 컨테이너 전체가 원본과 바이트 단위로 완전히 동일했다.

## 구현

`/tools/scripts/ys6_z.py`에 다음 기능을 추가했다.

- 비압축 데이터의 CRC32 계산
- 비압축 크기 기록
- zlib 레벨 0~9 압축
- `compress` 명령
- `roundtrip` 명령
- `--verify-only` 메모리 검증
- `--overwrite` 출력 보호
- 원본/재압축 SHA-256, 크기 차이, zlib 헤더 및 최초 차이 보고
- 컨테이너 동일성과 payload 동일성 분리 보고

## 컨테이너 생성 구조

```text
0x00  u32 LE  CRC32(uncompressed payload)
0x04  u32 LE  uncompressed payload size
0x08  bytes   zlib stream
```

기본 압축 레벨은 9이며 실제 원본 표본의 zlib 헤더 `78 DA`와 일치한다.

## 실제 표본 검증

- XSO `.z` 대표 표본: 31개
- 이미지 `title_000.dds.z`: 1개
- 총 검증: 32개

| 항목 | 결과 |
|---|---:|
| payload 동일 | 32 |
| payload 불일치 | 0 |
| 컨테이너 바이트 동일 | 32 |
| 컨테이너 불일치 | 0 |
| 원본 총 크기 | 85,145바이트 |
| 재압축 총 크기 | 85,145바이트 |
| 총 크기 차이 | 0바이트 |

- 32개 모두 원본과 재압축 SHA-256이 일치했다.
- 모든 `first_difference_offset`이 `null`이었다.
- 원본과 재압축 zlib 헤더는 모두 `78 DA`였다.
- CRC32, 비압축 크기, zlib 정상 종료 및 잔여 바이트 0 조건을 모두 통과했다.

## 단위 테스트

총 8개 테스트가 통과했다.

- 정상 컨테이너 검사
- 크기 불일치 거부
- 잘린 스트림 거부
- CRC32 불일치 거부
- 빈 데이터·ASCII·다국어 바이트·반복 데이터·전체 바이트 분포 압축
- 압축 레벨 0~9 검증
- 잘못된 압축 레벨 거부
- 최초 불일치 위치 계산

Python 바이트코드 컴파일도 통과했다.

## CLI

```powershell
python tools\scripts\ys6_z.py compress input.xso output.xso.z --level 9 --json
python tools\scripts\ys6_z.py roundtrip input.xso.z output.xso.z --level 9 --json
python tools\scripts\ys6_z.py roundtrip input.xso.z --verify-only --json
```

## 출력 보호 검증

- `--verify-only`: 출력 파일 생성 없음
- 최초 출력: 종료 코드 0
- 기존 출력에 `--overwrite` 없이 재실행: 종료 코드 2
- 생성 표본과 원본 SHA-256 일치

## 생성·변경 파일

- 수정: `/tools/scripts/ys6_z.py`
- 수정: `/tools/scripts/tests/test_ys6_z.py`
- 결과: `/docs/result/007-ys6-z-recompression-roundtrip.md`

## 임시 산출물

- `/.work/ys6-z-roundtrip`: 재압축 표본 32개와 검증 파일
- `/.work/ys6-z-roundtrip/roundtrip-results.json`: 파일별 결과
- `/.work/ys6-z-roundtrip/guard-test.z`: 덮어쓰기 보호 검증 표본

원본 게임 데이터이므로 Git에는 포함하지 않는다. 이슈 종료 시 임시 작업 폴더 전체를 정리할 수 있다.

## 원본 보호

- 원본 ISO 변경 없음
- 추출 원본 `.z` 변경 없음
- `/patched` 생성 또는 변경 없음

## 의미

- 현재 Python zlib 레벨 9 출력은 조사한 원본 제작 방식과 결정적으로 일치한다.
- 무수정 XSR 재조립과 `.z` 재압축을 연결해도 원본 `.xso.z`를 바이트 단위로 재현할 수 있다.
- 번역문 삽입 후에는 payload가 달라지므로 컨테이너 동일성 대신 CRC32·크기·재해제 내용 및 게임 수용성을 검증해야 한다.

## 알려진 제한

- 수정 문자열로 크기가 증가한 `.xso.z`는 아직 시험하지 않았다.
- ISO 내부 파일 교체와 LBA·할당 공간은 아직 분석하지 않았다.
- 에뮬레이터에서 재압축 파일의 로딩은 아직 검증하지 않았다.

## 다음 단계 권고

대표 XSR 문자열 하나를 같은 인덱스에서 변경하는 수정 PoC를 계획한다. 먼저 같은 바이트 길이의 CP932 일본어 교체로 XSR 재조립과 `.z` 재압축을 연결하고, 이후 별도 단계에서 문자열 길이 증가와 오프셋 재계산을 시험한다. ISO에 넣기 전 파일 교체 방식과 할당 공간을 조사해야 한다.

