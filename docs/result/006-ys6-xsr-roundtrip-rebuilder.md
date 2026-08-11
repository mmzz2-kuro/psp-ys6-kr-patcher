# Ys VI XSR 무수정 재조립 라운드트립 결과

## 상태

- 완료
- 사용자 승인: 2026-08-11

## 결론

XSR 파싱 결과를 사용해 문자열 상대 오프셋 테이블과 문자열 풀을 다시 구성한 결과, 실제 표본 31개가 모두 원본과 바이트 단위로 완전히 동일했다. XSR 파서와 무수정 재조립기의 기본 라운드트립 불변식이 성립한다.

## 구현

`/tools/scripts/ys6_xso.py`에 다음 기능을 추가했다.

- 원시 CP932 문자열 바이트 기반 XSR 재조립
- 문자열 상대 오프셋 테이블 재계산
- NUL 종료 및 엔트리별 패딩 보존
- `roundtrip` 명령
- 메모리 검증 전용 `--verify-only`
- 기존 출력 보호 `--overwrite`
- 원본/재조립 크기와 SHA-256 비교
- 최초 불일치 오프셋 계산
- UTF-8 JSON 결과

## 재조립 방식

다음 영역은 원본 바이트를 그대로 보존한다.

- XSR 헤더
- 바이트코드 명령 영역

다음 영역은 파싱 결과를 기준으로 다시 생성한다.

- 문자열 상대 오프셋 테이블
- 문자열 원시 CP932 바이트
- 문자열별 NUL 종료
- 원본과 같은 길이의 NUL 패딩

문자열은 디코딩된 텍스트를 다시 인코딩하는 대신 검증된 `raw_hex` 바이트를 사용했다.

## 실제 표본 검증

| 항목 | 결과 |
|---|---:|
| 검증 파일 | 31 |
| 바이트 동일 | 31 |
| 불일치 | 0 |
| 문자열 | 363 |
| 원본 총 크기 | 39,804바이트 |
| 재조립 총 크기 | 39,804바이트 |

- 각 파일의 원본 및 재조립 SHA-256이 일치했다.
- `first_difference_offset`은 전부 `null`이었다.
- 문자열 0개인 플래그 전용 XSR도 통과했다.

## 단위 테스트

총 10개 테스트가 통과했다.

- 정상 XSR 및 CP932 왕복
- 손상 매직, 카운트, 오프셋, NUL, CP932 거부
- 명령 영역 초과 거부
- 일본어·ASCII·빈 문자열·토큰·마크업 재조립
- 문자열 0개 XSR 재조립
- 최초 불일치 위치 계산

Python 바이트코드 컴파일도 통과했다.

## CLI 검증

```powershell
python tools\scripts\ys6_xso.py roundtrip input.xso output.xso --json
python tools\scripts\ys6_xso.py roundtrip input.xso --verify-only --json
```

- `--verify-only`: 출력 파일을 만들지 않고 동일성 검증 성공
- 최초 출력: 종료 코드 0
- 기존 출력에 재실행: 종료 코드 2로 덮어쓰기 거부
- 생성된 표본 출력과 입력 SHA-256 일치

## 생성·변경 파일

- 수정: `/tools/scripts/ys6_xso.py`
- 수정: `/tools/scripts/tests/test_ys6_xso.py`
- 결과: `/docs/result/006-ys6-xsr-roundtrip-rebuilder.md`

## 임시 산출물

- `/.work/ys6-xsr-roundtrip`: 재조립 XSR 31개와 검증용 파일
- `/.work/ys6-xsr-roundtrip/roundtrip-results.json`: 파일별 결과
- `/.work/ys6-xsr-roundtrip/guard-test.xso`: 덮어쓰기 보호 검증용 표본

원본 게임 데이터이므로 Git에는 포함하지 않는다. 이슈 종료 시 임시 작업 폴더 전체를 정리할 수 있다.

## 원본 보호

- 원본 ISO 변경 없음
- 원본 `.xso.z` 변경 없음
- `/patched` 생성 또는 변경 없음

## 알려진 제한

- 무수정 라운드트립만 검증했다.
- 번역문으로 문자열 길이가 변하는 경우는 아직 시험하지 않았다.
- `.z` 재압축 라운드트립은 아직 구현하지 않았다.
- XSR 파일 증가에 대한 런타임 버퍼 한계는 미검증이다.

## 다음 단계 권고

`.z` 래퍼의 재압축 기능을 구현하고, `decompress → recompress → decompress` 내용 동일성과 헤더 CRC32·비압축 크기를 검증한다. 압축 바이트 자체가 원본과 같아야 하는지와 게임이 다른 유효 zlib 스트림을 수용하는지는 분리해서 판단해야 한다.

