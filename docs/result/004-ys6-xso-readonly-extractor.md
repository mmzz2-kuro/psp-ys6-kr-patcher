# Ys VI XSO 읽기 전용 추출기 결과

## 상태

- 완료
- 사용자 승인: 2026-08-11

## 구현

- `/tools/scripts/ys6_xso.py`를 작성했다.
- 입력 XSO를 변경하지 않는 `info`, `dump`, `scan` 명령을 제공한다.
- 콘솔 및 JSON 출력은 UTF-8로 고정했다.
- 문자열 디코딩은 CP932를 명시하며 디코딩 후 재인코딩 바이트가 원본과 같은지 검사한다.
- JSON 파일은 기본적으로 기존 파일을 덮어쓰지 않으며 `--overwrite`가 있어야 교체한다.

## 구조 검증

도구는 다음 조건을 모두 검사한다.

- `XSR\0` 매직
- 최소 헤더 크기
- 명령 워드 및 문자열 테이블의 파일 범위
- 첫 문자열 상대 오프셋 0
- 문자열 오프셋의 엄격한 오름차순
- 문자열 풀 범위
- 각 문자열의 NUL 종료
- NUL 종료 뒤 정렬 패딩이 0인지 여부
- CP932 디코딩 및 바이트 왕복

## 명령

```powershell
python tools\scripts\ys6_xso.py info <input.xso> --json
python tools\scripts\ys6_xso.py dump <input.xso> --output <output.json>
python tools\scripts\ys6_xso.py scan <directory> --recursive --json
```

## 실제 표본 검증

- XSO 표본 5개 중 정상 5개, 오류 0개
- 총 문자열 63개 복원
- `\\n` 토큰 58회
- `\\x1` 토큰 5회
- `talkodo.xso`의 문자열 수 12개, 오프셋 테이블 `0x1F4`, 문자열 풀 `0x224` 재현
- `seltalk.xso`의 문자열 수 43개, 오프셋 테이블 `0x778`, 문자열 풀 `0x824` 재현
- UTF-8 JSON을 PowerShell에서 `-Encoding UTF8`로 다시 읽어 일본어와 토큰 보존을 확인했다.
- 기존 JSON 출력 파일에 `--overwrite` 없이 쓸 때 종료 코드 2로 거부되는 것을 확인했다.

## 단위 테스트

다음 6개 테스트가 모두 통과했다.

- 정상 XSR 및 CP932 왕복
- 잘못된 매직 거부
- 파일 범위를 벗어난 카운트 거부
- 비단조 문자열 오프셋 거부
- NUL 종료 누락 거부
- CP932 디코딩 오류 거부

Python 바이트코드 컴파일도 통과했다.

## 생성·변경 파일

- `/tools/scripts/ys6_xso.py`
- `/tools/scripts/tests/test_ys6_xso.py`
- `/docs/result/004-ys6-xso-readonly-extractor.md`

## 임시 산출물

- `/.work/ys6-initial/talkodo.json`에 UTF-8 JSON 표본이 있다.
- 기존 해제 XSO 표본은 `/.work/ys6-initial/decompressed`에 있다.
- 원본 ISO와 `/patched`는 변경하지 않았다.

## 알려진 제한

- 바이트코드는 원시 워드 수와 경계만 검사하며 opcode 의미는 아직 해석하지 않는다.
- 문자열 수정 및 XSR 재조립 기능은 없다.
- `.xso.z`를 직접 입력받지는 않으므로 먼저 `ys6_z.py`로 해제해야 한다.
- 현재 전체 ISO가 아닌 대표 표본 5개에서 검증했다.

## 다음 단계

- 더 많은 XSO 파일을 선택적으로 추출·해제하여 포맷 변형과 전체 토큰 종류를 조사한다.
- 바이트코드에서 문자열 인덱스를 참조하는 명령을 찾아 선택지·화자·표시 순서를 연결한다.
- 이후 별도 계획으로 XSR 무수정 재조립 라운드트립을 구현한다.
