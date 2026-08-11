# Ys VI 폰트 렌더러 분석 및 한글 단일 글리프 PoC 결과

## 상태

- 구현: 완료
- 정적 검증: 완료
- PPSSPP 인게임 검증: 실패 — 교체 전 `傲` 글리프 표시

## 폰트 및 렌더러 판정

- 대사 출력은 PSP 시스템 `libfont.prx`나 `sceFont*` API를 사용하지 않는다.
- 게임 본체가 CP932 바이트를 직접 읽어 자체 내장 비트맵 글리프에 대응시킨다.
- 선행 바이트 판정표 주소: `0x0895FC38`
- 코드→글리프 인덱스 함수: `0x0882CB94`
- 글리프 렌더링 함수: `0x0882CFFC`
- `BOOT.BIN` 폰트 테이블 파일 오프셋: `0x0013E88C`

폰트 테이블은 4,608개의 26바이트 레코드로 구성된다.

| 필드 | 크기 |
|---|---:|
| CP932 코드 | 2바이트 |
| 16×12 1bpp 비트맵 | 24바이트 |

렌더러는 글리프 인덱스를 가로 16칸 아틀라스 좌표로 변환한다. 셀 폭은 16px, 높이는 12px다.

## 한글 글리프

- 원본 글꼴: `C:/Windows/Fonts/gulim.ttc`
- 글꼴 면: Gulim Regular, TTC 인덱스 0
- 크기: 12px
- 대상 문자: `한`
- 대체 CP932 코드: `0x98FC`
- 기존 문자: `傲`
- 글리프 인덱스: 4605
- 레코드 파일 오프셋: `0x0015BC3E`
- 비트맵 파일 오프셋: `0x0015BC40`
- 변경된 비트맵 바이트: 22바이트/24바이트

전체 추출 문자열 7,424개를 기준으로 `0x98FC`의 사용 횟수는 0이다. `gulim.ttc` 자체는 저장소나 결과물에 복사하지 않았고 렌더링된 단일 24바이트 비트맵만 반영했다.

## 시작 대사 PoC

- 대상: `PSP_GAME/USRDIR/data/arc/s_0551.bin`
- 내장 파일: `s_0551.xso.z`
- 문자열 인덱스: 35
- 시험 문자열: `0x98FC` 1글자 + 전각 공백 10개
- 기존 길이와 시험 길이: 각각 22바이트

게임에서는 `0x98FC`가 수정된 글리프 `한`으로 표시돼야 한다.

## 결과 ISO

- 경로: `/patched/014-hangul-glyph-poc/Ys VI - hangul-glyph-poc.iso`
- 크기: 866,254,848바이트
- SHA-256: `E8FB55D2D2B76427A97CC977662CF29C54CDD3E8BE9E36F588B2FFAED345711B`

## 내부 파일 해시

| 파일 | SHA-256 |
|---|---|
| 수정 `BOOT.BIN` | `9622C70F1B6CC75E2F1BACE1EE7810EE0DAEA0CEA0BE37640C417226451E9C5A` |
| 수정 `s_0551.bin` | `458DFF952C81532DD0B4B0964701FAF75C475D7D3BA564D3BD96610BC50068D4` |
| 수정 `s_0551.xso.z` | `AE1CB04E1871EF9FF48390AA4A7DA5BF9F2E1126CAD5B9CCF5868C5B1952D2A1` |
| 수정 XSR | `0791D00C0E06FFB1448057CFCEE2D32498955A4EB91BD79C0D02C0798E09AC80` |

## 검증

- 최종 ISO에서 `BOOT.BIN`과 `s_0551.bin`을 다시 읽어 준비 파일과 SHA-256이 일치함을 확인했다.
- 기준 작업 ISO와 비교한 변경은 대사 아카이브 할당 범위와 `BOOT.BIN` 글리프 비트맵 범위에만 존재한다.
- 허용 범위 밖 변경: 0건
- 원본 ISO SHA-256 유지: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 전체 단위 테스트: 38개 통과
- PPSSPP 원격 디버거 설정은 원래 값인 `False`로 복원했다.

## 생성·변경 파일

- 추가: `/tools/scripts/ys6_font_table.py`
- 추가: `/tools/scripts/ys6_font_patch.py`
- 추가: `/tools/scripts/ys6_vram_render.py`
- 추가: `/tools/scripts/nodejs/ys6_ppsspp_memory_dump.js`
- 추가: `/tools/scripts/tests/test_ys6_font_tools.py`
- 갱신: `/docs/plan/014-ys6-font-renderer-hangul-glyph-poc.md`
- 추가: `/docs/result/014-ys6-font-renderer-hangul-glyph-poc.md`

## 작업 자료 및 정리

- 분석·추출 자료: `/.work/ys6-font-renderer-poc`
- 검증용 중간 ISO는 최종본 생성 후 삭제했다.
- 보존할 수정 ROM은 `/patched/014-hangul-glyph-poc`의 PoC ISO 한 개다.

## 남은 확인

## 인게임 실패 결과

PPSSPP에서 PoC ISO로 새 게임을 시작했을 때 첫 대사에 `한`이 아니라 대체 대상의 원래 글리프 `傲`가 표시됐다.

- `0x98FC` 대사 코드는 정상 적용됨: 수정 `s_0551.bin`은 런타임에서 사용된다.
- `BOOT.BIN` 비트맵 교체는 미적용: 실행 중 폰트 테이블은 수정 전 상태다.
- 가장 유력한 원인: PPSSPP가 실제 부팅에 `PSP_GAME/SYSDIR/EBOOT.BIN`을 사용하고 평문 `BOOT.BIN` 변경은 실행 이미지에 반영하지 않는다.
- 글리프 모양 또는 임계값 문제가 아니다. 스크린샷의 글자는 수정 전 `0x98FC` 글리프와 일치한다.

이 결과로 PoC ISO는 정적 구조 검증용이며 성공한 한글 패치 결과물로 취급하지 않는다. 다음 단계에는 `EBOOT.BIN`의 복호화·재패킹 가능성 또는 PPSSPP의 복호화 EBOOT 덤프 적용 경로 조사가 필요하다. 계획에 명시된 중단 조건에 따라 사용자 확인 전에는 해당 작업을 진행하지 않는다.
