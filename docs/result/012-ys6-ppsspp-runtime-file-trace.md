# Ys VI PPSSPP 런타임 대사 파일 추적 결과

## 상태

- 수정 ISO 실행 경로 확인: 완료
- 런타임 메모리 추적: 완료
- 실제 데이터 원본 식별: 완료
- PPSSPP 진단 설정 복원: 완료

## 결론

사용자는 올바른 수정 ISO를 실행하고 있었다. 게임은 개별 `data/map/s_05/s_0551/s_0551.xso.z`가 아니라 통합 아카이브 `data/arc/s_0551.bin` 안의 원본 복사본을 읽었다. 따라서 기존 ISO 패치는 정적으로는 정확했지만 런타임 대상이 아니어서 첫 대사가 바뀌지 않았다.

## PPSSPP 실행 확인

- 프로세스: `D:/game/psp/emul/ppsspp_win/PPSSPPWindows64.exe`
- 게임 ID: `ULJM05009`
- 게임 버전: `1.05`
- PPSSPP가 부팅한 ISO: `/patched/009-talkkebin-string-poc/Ys VI - first-dialogue-poc.iso`
- 세이브 스테이트가 아닌 새 게임으로 사용자 확인

파일 로그에도 수정 ISO 부팅 경로가 기록됐다. ISO 선택 오류라는 초기 가설은 폐기했다.

## 런타임 메모리 증거

PPSSPP localhost 전용 디버거로 PSP 사용자 메모리를 읽었다.

- 원문 `どうしたの、イーシャ？`: 2개 주소에서 발견
  - `0x08D0A8C0`: 화면 출력용 마크업 버퍼
  - `0x09529C72`: 로드된 XSR 문자열 풀 내부
- 시험문 `これはテスト表示です。`: 0건
- 원본 `s_0551.xso` 4,516바이트 전체: `0x09528E60`에서 완전 일치
- 수정 XSR 전체: 0건

메모리 기록 정보는 원본 XSR이 게임 루틴에 의해 힙에 복사됐음을 보여 줬다.

## 숨은 복사본 식별

수정 ISO 전체 원시 바이트를 검색한 결과:

| 항목 | ISO 절대 오프셋 |
|---|---:|
| 통합 아카이브 안 원본 `.xso.z` | `0x08779000` |
| 개별 수정 `.xso.z` | `0x14D10000` |

`0x08779000`을 포함하는 ISO 파일은 다음과 같다.

- 경로: `PSP_GAME/USRDIR/data/arc/s_0551.bin`
- ISO 시작 오프셋: `0x08778000`
- ISO LBA: 69,360
- 크기: 1,165,312바이트
- 원본 SHA-256: `93049B6E8CD72B4EE80F83C04016891CEA0FD06011EE13F92CBC12E43E554D02`
- 내장 `s_0551.xso.z` 상대 오프셋: `0x1000`

수정 ISO의 파일시스템 `.z` 8,459개를 전수 해제한 결과 개별 수정 XSR은 정상적으로 존재했고 원본 XSR은 파일 엔트리에서 제거돼 있었다. 그러나 `s_0551.bin` 내부는 별도 아카이브 복사본이어서 그대로 남아 있었다.

## 아카이브 헤더 예비 확인

`s_0551.bin`의 첫 `0x1000`은 파일 테이블이며 내장 데이터는 `0x800` 경계로 배치된다.

`s_0551.xso.z` 엔트리:

- 이름 필드 시작: `0x144`
- 데이터 오프셋 필드: `0x164`, 값 `0x1000`
- 크기 필드: `0x168`, 값 `0x79A`(1,946바이트)
- 다음 엔트리 데이터 시작: `0x1800`
- 현재 할당 공간: 2,048바이트

수정 `.xso.z`는 1,951바이트이므로 같은 할당 공간 안에 들어가며 크기 필드만 5바이트 증가시키면 된다.

## 진단 도구 및 자료

- 추가: `/tools/scripts/ys6_iso_z_search.py`
- 메모리 덤프: `/.work/ys6-ppsspp-runtime-trace/user-memory.bin`
- 파일 로그: `/.work/ys6-ppsspp-runtime-trace/first-dialogue-log.txt`
- 설정 백업: `/.work/ys6-ppsspp-runtime-trace/ppsspp.ini.before`
- 아카이브 추출본: `/.work/ys6-arc-s0551/PSP_GAME/USRDIR/data/arc/s_0551.bin`

## 설정 복원

- `FileLogging = False`
- `FILESYSLevel = 2`
- `LOADERLevel = 2`
- `IOLevel = 2`
- `RemoteDebuggerOnStartup = False`
- `RemoteDebuggerLocal = False`

PPSSPP 진단 설정은 원래 값으로 복원했다. 세이브와 세이브 스테이트는 변경하지 않았다.

## 알려진 문제

- ISO 전수 `.z` 검사에서 `s_9021__w.yco.z` 한 파일은 일반 zlib 컨테이너가 아니어서 해제 오류로 분류됐다. 이번 대사와 무관하다.
- 기존 결과 문서 011은 개별 XSO 패치가 정적으로 성공했다는 사실은 유효하지만, 런타임 성공 결과로 볼 수 없다.

## 다음 단계

`s_0551.bin` 파일 테이블을 검증·재구성하는 전용 스크립트를 작성하고, 아카이브 내부 `s_0551.xso.z`를 수정한 뒤 기존 작업 ISO 하나를 갱신한다.
