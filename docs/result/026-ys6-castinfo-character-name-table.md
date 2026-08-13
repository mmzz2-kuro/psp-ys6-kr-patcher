# Ys VI castinfo 공통 인물명 테이블 한글화 결과

## 상태

- 작업 번호: 026
- 구현: 완료
- 정적 검증: 완료
- 인게임 검증: 완료
- 완료일: 2026-08-13

## 결과 요약

대화창의 인물명은 개별 `talk*.xso.z`가 아니라 공통 캐릭터 테이블 `castinfo.dat`에서 로드되는 것을 확인했다. `CAST_C240`의 이름 필드를 게임 한글 코드로 수정하고 standalone과 `init.bin` 내부 두 사본에 함께 반영했다.

최종 ISO에서 사용자가 이전과 동일한 이샤 대화 화면에 도달해 인물명 `이샤`가 정상 출력되는 것을 확인했다. 이에 `castinfo.dat`를 대화창 공통 인물명 정본으로 확정한다.

## 원인 분석

다음 XSO를 각각 수정했지만 인게임 이름은 일본어로 유지됐다.

- `s_9000/talkisha.xso.z`
- `s_hidden1/talkisha.xso.z`

전체 대사 XSO 카탈로그에는 일반 `アドル`이 없었고, 원본 ISO CP932 검색으로 공통 데이터 테이블을 발견했다.

- `アドル` 검색 결과는 챌린지용 특수 캐릭터 `ブラックアドル` 두 사본뿐
- `イーシャ` 화자명은 `castinfo.dat`의 `CAST_C240` 레코드에 존재
- `talkisha`의 `イーシャ1/2/3`은 공통 화자명 필드가 아님

## castinfo 구조

- 파일 크기: 21,264바이트
- 원본 SHA-256: `B91C22FC17C6E39A7B9DA8800099A598FB89FEB8ED262112142DD20736E2C730`
- 레코드 식별자: `CAST_C240`
- 이름 필드 오프셋: `0x2D20`
- 이름 필드 크기: 32바이트
- 원문: CP932 `イーシャ` + NUL 패딩

동일한 원본 사본:

1. `PSP_GAME/USRDIR/data/misc/castinfo.dat`
2. `PSP_GAME/USRDIR/data/arc/init.bin` 엔트리 8 `castinfo.dat`

`init.bin` 엔트리 정보:

- index: 8
- flags: `0x01000000`
- 할당: 22,528바이트
- 두 원본 사본은 바이트 단위로 동일

## 한글 인코딩

- `이`: 게임 코드 `0x98EF`
- `샤`: 게임 코드 `0x98ED`
- 이름 필드: `98EF98ED` 뒤 28바이트 NUL 패딩
- 수정 필드 내 변경 바이트: 8개
- 수정 파일 크기: 21,264바이트 유지
- 수정 SHA-256: `89FA96CB785AAC59B55E2179C5DA0EFFF548025A3C65697DF04CCDE414AD3572`

standalone과 `init.bin` 내부 수정 사본의 SHA-256이 완전히 일치한다.

## 최종 ISO

- 경로: `/patched/026-castinfo-character-name-table/Ys VI - castinfo-isha-korean-build.iso`
- SHA-256: `92BDAC735A0271BF013E86AAB2EA57659D9563D43910F1C1AC8E4C7AB7FDFF94`

누적 내용:

- 검수 번역: 115개
- XSO: 31개
- 아카이브: 기존 번역 아카이브 4개 + `init.bin`
- standalone XSO: 38개
- 공통 `castinfo.dat`: 1개
- 한글 글리프: 192개
- ISO 교체 파일: 45개

## 검증 결과

- 이름 필드 밖 `castinfo.dat` 변경 0건
- `init.bin` 대상 엔트리 밖 변경 0건
- `init.bin` 크기 1,570,816바이트 유지
- `init.bin` 엔트리 index·flags·할당 유지
- ISO 허용 extent 및 길이 필드 밖 변경 0건
- 모든 글리프 bbox 왼쪽 시작점 `x=1`
- 자동 테스트 84개 통과
- Python 바이트코드 컴파일 통과
- 원본 및 기존 025 ISO SHA-256 유지

사용자 인게임 확인:

- 이샤 인물명 한글 정상 출력
- 대사 본문 정상
- 확인된 이벤트 진행 이상 없음

## 생성·변경 파일

- 추가: `/tools/scripts/ys6_castinfo.py`
- 추가: `/tools/scripts/tests/test_ys6_castinfo.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 생성: `/.work/ys6-castinfo-character-name-table`
- 생성: 최종 026 ISO

## 알려진 사항 및 정리 대상

- `ブラックアドル`은 챌린지용 특수 캐릭터 또는 몬스터 계열 명칭으로 이번 범위에서 제외했다.
- 일반 주인공 이름은 `castinfo.dat`에서 별도 `アドル` 레코드로 확인되지 않았다.
- 인물명 정본이 `castinfo.dat`로 확정됐으므로 다음 실험용 `talkisha` 변경은 화자명 출력에 불필요하다.
  - `s_9000/talkisha`: `이샤1/2/3`, `이샤`
  - `s_hidden1/talkisha`: `이샤`
- 해당 실험 변경은 현재 누적 검수본에 남아 있다. 다음 누적 빌드 정리 단계에서 제거 여부를 계획하고 사용자 확인 후 처리한다.
- 이전 이샤 진단 ISO들은 최종본이 아니며 필요하면 후속 정리에서 삭제할 수 있다.
