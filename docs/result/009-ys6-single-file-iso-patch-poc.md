# Ys VI 단일 파일 ISO 패치 PoC 결과

## 상태

- 정적 패치 및 검증: 완료
- 에뮬레이터 인게임 검증: 미수행(PPSSPP 환경 없음)
- 사용자 승인: 2026-08-11

## 결론

원본 ISO를 변경하지 않고 `/patched`에 단일 작업 ISO를 생성해 `talkkebin.xso.z`를 기존 LBA에 제자리 교체했다. ISO 9660 양방향 파일 크기 필드를 함께 갱신했으며, 작업 ISO에서 파일을 재추출해 수정 `.z`·XSR·시험 문자열까지 정적으로 검증했다.

## 작업 ISO

- 경로: `/patched/009-talkkebin-string-poc/Ys VI - talkkebin-poc.iso`
- 크기: 866,254,848바이트
- SHA-256: `B0DA72EF98FDB4C97AD7CFE40AC735C55C913E7106CF231A3A2597CDC60C389A`
- 원본과 같은 전체 크기
- 이번 이슈에서 생성한 ISO 작업본은 이 파일 하나뿐이다.

## 원본

- 경로: `/roms/Ys VI - Napishtim no Hako (Japan).iso`
- SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 작업 후에도 SHA-256이 동일하다.

## 구현

`/tools/scripts/ys6_iso_patch.py`를 추가했다.

주요 안전장치:

- 기대 원본 ISO SHA-256 검사
- 기대 대상 파일 크기·SHA-256 검사
- 원본/출력 동일 경로 거부
- ISO 9660 extent 및 LE/BE 메타데이터 교차 검사
- 기존 할당 공간 초과 거부
- 기존 출력 기본 거부
- 대상 데이터 재독해 검증
- 전체 ISO diff 및 허용 범위 밖 변경 거부

전체 diff는 동일한 1 MiB 청크를 즉시 건너뛰도록 최적화했다. 최초 실행은 비효율적인 바이트별 비교로 60초 제한에 걸렸으나, 작업 ISO 크기와 상태를 확인한 뒤 동일 작업본 하나만 명시적으로 재초기화하여 성공했다. 추가 ISO는 만들지 않았다.

## 적용 내용

### 대상 엔트리

- 내부 경로: `PSP_GAME/USRDIR/data/map/s_00/s_0000/talkkebin.xso.z`
- LBA: 156,320
- extent 바이트 오프셋: 320,143,360
- 디렉터리 레코드 오프셋: 501,018

### 크기

| 항목 | 값 |
|---|---:|
| 원본 파일 | 538바이트 |
| 수정 파일 | 549바이트 |
| 증가 | 11바이트 |
| 할당 공간 | 2,048바이트 |
| 수정 후 여유 | 1,499바이트 |

### 쓰기

- 기존 LBA에 수정 `.z` 549바이트 기록
- 같은 할당 섹터의 나머지 영역 0 패딩
- ISO 9660 little-endian 논리 크기 549 기록
- ISO 9660 big-endian 논리 크기 549 기록
- LBA 및 후속 파일 배치 변경 없음

## 전체 ISO 변경 범위 검증

- 허용 범위 밖 변경: 0개
- 변경은 다음에만 존재한다.
  - 디렉터리 레코드 LE 크기 필드
  - 디렉터리 레코드 BE 크기 필드
  - LBA 156,320의 기존 한 섹터 내부
- 작업 ISO 전체 크기는 원본과 같다.

상세 연속 diff 범위는 `/.work/ys6-string-poc/iso-patch-result.json`에 기록했다.

## 작업 ISO 재추출 검증

7-Zip으로 작업 ISO에서 대상 파일을 다시 추출했다.

| 검증 | 결과 |
|---|---|
| 재추출 크기 | 549바이트 |
| 재추출 `.z`와 준비한 수정 `.z` SHA-256 | 동일 |
| `.z` CRC32 | `F7C830AF`, 정상 |
| `.z` 비압축 크기 | 892바이트, 정상 |
| zlib 종료 | 정상 |
| 잔여 스트림 바이트 | 0 |
| 재해제 XSR과 준비한 수정 XSR SHA-256 | 동일 |
| XSR 구조 | 정상 |
| XSR 문자열 인덱스 4 | `これは動作確認用の文章です。` |
| 패치 후 엔트리 LBA | 156,320 |
| 패치 후 논리 크기 | 549바이트 |

## 출력 보호

- 이미 존재하는 작업 ISO에 `--overwrite` 없이 재실행 시 종료 코드 1로 거부
- 거부 전후 작업 ISO SHA-256 동일
- 원본과 작업본 경로가 같으면 거부

## 테스트

- ISO 패치 테스트 5개 통과
- XSR 테스트 14개 통과
- `.z` 테스트 8개 통과
- 전체 27개 테스트 통과
- Python 바이트코드 컴파일 통과

테스트 범위:

- 할당 공간 이내 교체
- 할당 공간 초과 거부
- 원본/출력 동일 경로 거부
- 기존 출력 보호
- LE/BE 메타데이터 불일치 거부
- 허용 범위 diff 검사

## 생성·변경 파일

- 추가: `/tools/scripts/ys6_iso_patch.py`
- 추가: `/tools/scripts/tests/test_ys6_iso_patch.py`
- 생성: `/patched/009-talkkebin-string-poc/Ys VI - talkkebin-poc.iso`
- 결과: `/docs/result/009-ys6-single-file-iso-patch-poc.md`

## 임시 검증 자료

- `/.work/ys6-string-poc/iso-patch-result.json`
- `/.work/ys6-iso-poc/verification-summary.json`
- `/.work/ys6-iso-poc/iso-entry.json`
- `/.work/ys6-iso-poc/talkkebin-from-patched-iso.xso`
- `/.work/ys6-iso-poc/talkkebin-from-patched-iso.json`
- 재추출 `.xso.z` 트리

원본 게임 데이터이므로 Git에는 포함하지 않는다.

## 에뮬레이터 검증 상태

- PPSSPP 실행 파일이 PATH에 없음
- 일반 설치 경로와 저장소 내부에서도 발견되지 않음
- 따라서 부팅, 대상 NPC 접근 및 인게임 문구 표시는 아직 검증하지 않았다.
- 이번 결과는 정적 ISO 패치 성공이며 인게임 성공 판정은 아니다.

## 작업 ISO 정리 상태

- 작업 ISO는 후속 PPSSPP 검증을 위해 유지한다.
- 경로는 `/patched/009-talkkebin-string-poc` 한 곳으로 제한돼 있다.
- 인게임 검증 완료 또는 이슈 폐기 시 삭제 여부를 결정할 수 있다.

## 다음 단계 권고

PPSSPP 환경을 준비한 뒤 작업 ISO 부팅과 대상 NPC 대사를 확인한다. 인게임 표시가 성공하면 다음 기술 단계는 길이가 달라지는 문자열의 XSR 오프셋 재계산 PoC이며, 한글 표시 자체는 별도로 폰트·인코딩·렌더러 분석과 `BOOT.BIN` 정적 분석이 필요하다.

