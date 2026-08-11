# Ys VI 복호화 EBOOT 한글 단일 글리프 PoC 결과

## 상태

- 구현: 완료
- 정적 검증: 완료
- PPSSPP 인게임 검증: 성공

## 결론

PPSSPP가 ISO의 암호화 `EBOOT.BIN`을 실제 부팅에 사용하기 때문에 평문 `BOOT.BIN`만 수정한 계획 014의 패치는 적용되지 않았다. PPSSPP의 복호화 EBOOT 덤프를 수정해 ISO의 `PSP_GAME/SYSDIR/EBOOT.BIN`에 넣은 결과, 외부 치트·플러그인·텍스처팩 없이 ISO 단독으로 한글 글리프가 출력됐다.

사용자가 세이브 스테이트 없이 새 게임 첫 대사를 확인했고, 최종 보정본에서 `한`이 정상적으로 표시됐다.

## 복호화 EBOOT

- 덤프 경로: `/.work/ys6-decrypted-eboot-poc/ULJM05009_EBOOT.BIN`
- 형식: 32비트 ELF
- 크기: 1,935,840바이트
- SHA-256: `EB20970858EC420FB1E068C38DFF5765CD3C99FC624266E2989DAC92E39108E5`
- 기존 평문 `BOOT.BIN`과 공통 길이 1,935,501바이트 전체가 동일하다.
- 폰트 테이블은 양쪽 모두 파일 오프셋 `0x0013E88C`에 존재한다.

PPSSPP 설정의 `DumpFileTypes`는 덤프 후 기존 값 `0`으로 복구했으며 원격 디버거 설정도 비활성 상태다.

## 한글 글리프 패치

- 대상 코드: `0x98FC`
- 기존 문자: `傲`
- 글리프 인덱스: 4605
- 레코드 오프셋: `0x0015BC3E`
- 비트맵 오프셋: `0x0015BC40`
- 형식: 16×12, 1bpp, 24바이트
- 수정 EBOOT SHA-256: `603AEC5645AF247D8247AA7F86C0ED02690D2EB48C5812588FC1439D169E4A01`

초기 `gulim.ttc` 자동 래스터 결과는 오른쪽 `ㅏ` 가로획이 렌더러의 실제 가시 폭에서 잘렸다. 획을 두껍게 하는 방식은 해결책이 아니었으며, 최종본은 글리프 구성 전체를 왼쪽 안전 영역으로 이동해 `ㅎ·ㅏ·ㄴ`이 모두 보이도록 했다.

재현 가능한 수동 글리프 패치를 위해 `ys6_font_patch.py`에 12행×16열의 `.`/`#` 패턴 파일 입력 기능을 추가했다.

## 대사 PoC

- 대상: `PSP_GAME/USRDIR/data/arc/s_0551.bin`
- 내장 파일: `s_0551.xso.z`
- 문자열 인덱스: 35
- 시험 코드: `0x98FC`
- 수정 아카이브 SHA-256: `458DFF952C81532DD0B4B0964701FAF75C475D7D3BA564D3BD96610BC50068D4`

## 최종 ISO

- 경로: `/patched/015-decrypted-eboot-hangul-poc/Ys VI - decrypted-eboot-hangul-poc.iso`
- 크기: 866,254,848바이트
- SHA-256: `4963FE9BBD0BD315B740202AD3879C2B2F375B3982B3E5E0E052473C3491D997`

원본 ISO는 변경하지 않았다.

- 원본 SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 최종 ISO 내부 EBOOT SHA-256: `603AEC5645AF247D8247AA7F86C0ED02690D2EB48C5812588FC1439D169E4A01`
- 최종 ISO 내부 `s_0551.bin` SHA-256: `458DFF952C81532DD0B4B0964701FAF75C475D7D3BA564D3BD96610BC50068D4`
- 원본 대비 허용 범위 밖 변경: 0건

## 검증

- 수정 EBOOT와 ISO에서 재확인한 EBOOT의 크기·SHA-256 일치
- 수정 대사 아카이브와 ISO에서 재확인한 아카이브의 크기·SHA-256 일치
- EBOOT 및 대사 아카이브의 기존 ISO 할당 범위 내 제자리 교체
- 전체 단위 테스트 39개 통과
- `python -m compileall -q tools/scripts` 통과
- PPSSPP ISO 단독 부팅 성공
- 사용자 인게임 `한` 출력 확인

## 생성·변경 파일

- 갱신: `/tools/scripts/ys6_font_patch.py`
- 갱신: `/tools/scripts/tests/test_ys6_font_tools.py`
- 갱신: `/docs/plan/015-ys6-decrypted-eboot-hangul-glyph-poc.md`
- 추가: `/docs/result/015-ys6-decrypted-eboot-hangul-glyph-poc.md`
- 생성: `/patched/015-decrypted-eboot-hangul-poc/Ys VI - decrypted-eboot-hangul-poc.iso`

게임 원본 데이터, 덤프 EBOOT 및 작업용 글리프 패턴은 `/.work/ys6-decrypted-eboot-poc`에만 두고 Git 대상에는 포함하지 않는다.

## 정리 및 남은 범위

- 중간 테스트 ISO는 모두 삭제했다.
- `/patched/015-decrypted-eboot-hangul-poc`에는 성공한 최종 PoC ISO 한 개만 남겼다.
- 이번 결과는 `한` 한 글자의 렌더링 경로를 검증한 PoC다. 전체 한글 패치에는 사용 가능한 CP932 코드 슬롯 배정, 다수 글리프 생성·가시 폭 보정, 문자열 인코딩 및 자동 패치 도구 확장이 추가로 필요하다.
