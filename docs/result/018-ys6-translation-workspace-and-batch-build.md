# Ys VI 번역 작업공간 및 다중 문자열 일괄 빌드 결과

## 상태

- 구현: 완료
- 정적 검증: 완료
- GUI 사용자 확인: 성공
- PPSSPP 인게임 검증: 성공

## 결론

전체 7,424개 문자열을 원문과 번역문으로 관리하는 번역 작업공간, GUI 편집 기능 및 검수 완료 번역을 한 XSO에 일괄 적용하는 빌드 기반을 구현했다. 연속된 두 문자열에 길이 증가와 감소를 동시에 적용한 PoC가 PPSSPP에서 정상 출력됐으며 이후 이벤트도 정상 진행됐다.

카탈로그의 standalone `s_0551.xso.z`와 실제 런타임 `s_0551.bin` 내 XSO의 비압축 payload SHA-256이 일치해 이번 대상의 대응 관계도 확인했다.

## 번역 작업공간

- 정본: UTF-8 JSON
- 교환 형식: UTF-8 BOM CSV
- 전체 레코드: 7,424개
- 고유 키: `iso_path + string_index`

주요 필드:

- 원본 경로·맵·XSO·문자열 인덱스·역할
- 원문 텍스트·원시 HEX·SHA-256
- 번역문·상태·메모

지원 상태:

- `untranslated`
- `draft`
- `reviewed`
- `excluded`
- `conflict`
- `orphaned`

동기화 시 번역·상태·메모를 보존한다. 같은 키의 원문 SHA-256이 바뀌면 `conflict`, 카탈로그에서 사라지면 `orphaned`로 표시한다.

## 검증

번역 검증기는 다음 오류를 빌드 전에 차단한다.

- 중복 키와 필수 필드 누락
- 잘못된 원문 HEX·SHA-256
- 지원하지 않는 상태
- 검수 완료 상태의 빈 번역
- `\n`, `\s`, `\xN` 제어 토큰 불일치
- `<color>`, `<ruby>`, `<endruby>`, `<scale>` 마크업 불일치
- 번역문 NUL 포함

번역문이 있지만 상태가 검수 완료가 아니면 경고하며, 실제 빌드는 `reviewed` 레코드만 사용한다.

## GUI

`/tools/ys6_dialogue_viewer.py`를 번역 편집기로 확장했다.

- 기존 카탈로그 검색·역할 필터·상세 보기 유지
- 번역 JSON 작업공간 열기
- 번역문, 상태 및 메모 편집
- 현재 항목 반영 및 JSON 저장
- 원문과 번역문 동시 목록 표시
- 검색 대상에 번역문 포함
- UTF-8 BOM CSV 내보내기
- CSV 가져오기 시 키와 원문 SHA-256 검증

GUI는 번역 파일만 수정하며 게임 데이터, EBOOT, 아카이브 및 ISO를 직접 수정하지 않는다. 사용자가 번역·상태·메모 편집과 저장이 정상 동작함을 확인했다.

## 다중 문자열 빌드

`ys6_translation_build.py`는 다음 절차로 한 XSO를 빌드한다.

1. 작업공간 전체 검증
2. 대상 ISO 경로의 `reviewed` 레코드 선택
3. 현재 XSO 원문 바이트와 작업공간 SHA-256 비교
4. 한글 매핑으로 번역문을 2바이트 게임 코드로 인코딩
5. 여러 문자열을 한 번에 가변 길이 재조립
6. 수정 XSO 재파싱 및 각 교체 바이트 역검증
7. 문자열별 원본·수정 길이와 전체 증감량 보고

원문이 다르거나 매핑되지 않은 문자가 있으면 출력 XSO를 만들지 않는다.

## 런타임 아카이브 대응

- 카탈로그 경로: `PSP_GAME/USRDIR/data/map/s_05/s_0551/s_0551.xso.z`
- 런타임 아카이브: `PSP_GAME/USRDIR/data/arc/s_0551.bin`
- 런타임 엔트리: `s_0551.xso.z`
- 양쪽 비압축 XSO SHA-256: `1BA1D501FEF350045691CA15F3A4F99205623C829F3B916FEA566E3978175614`

따라서 `s_0551`은 이름뿐 아니라 payload 해시까지 일치한다. 전체 아카이브 대응표 생성은 ISO 내 `/data/arc` 전체 열거가 필요한 후속 범위로 남는다.

## 다중 문자열 PoC

| 인덱스 | 원문 길이 | 번역문 | 번역 길이 | 증감 |
|---:|---:|---|---:|---:|
| 35 | 22 | `한글출력테스트입니다입니다` | 26 | +4 |
| 36 | 16 | `테스트입니다` | 12 | -4 |

- XSO 전체 크기: 4,516바이트로 동일
- 수정 XSO SHA-256: `5D7BDB912B0001B2BBA5D4967FD5961ADF98EDF9961FA6107C40A242B506FF84`
- 수정 `.xso.z` 크기: 1,957바이트
- 수정 `.xso.z` SHA-256: `82C5443933A66644A58F52476005B5EF081E83C64A465271378DB96B2F3B83D8`
- 아카이브 할당 공간: 2,048바이트
- 남은 여유: 91바이트
- 수정 `s_0551.bin` SHA-256: `B4CCE2ED110229F218146F31A8CBBAB1853B0433F83F79F3F13165E81B8C0E99`

사용자가 PPSSPP 새 게임에서 첫 번째와 두 번째 번역문이 정상 출력되고 후속 이벤트도 정상 진행됨을 확인했다.

## 최종 ISO

- 경로: `/patched/018-translation-batch-poc/Ys VI - translation-batch-poc.iso`
- 크기: 866,254,848바이트
- SHA-256: `3E43F6ACBB8C1B9DFD961E85DF5804144031A8B29E92F4D33CC1B2DB271CB681`

내부 파일:

| 파일 | SHA-256 |
|---|---|
| 수정 `EBOOT.BIN` | `DAB8C59FCC0913EF6A7D2FEB4A62DF0ABC5728B8F0BDDA7EA0581A695484970D` |
| 수정 `s_0551.bin` | `B4CCE2ED110229F218146F31A8CBBAB1853B0433F83F79F3F13165E81B8C0E99` |

- 원본 ISO SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`
- 원본 대비 허용 범위 밖 변경: 0건
- 중간 ISO: 최종 검증 후 삭제

## 생성·변경 파일

- 갱신: `/tools/ys6_dialogue_viewer.py`
- 추가: `/tools/scripts/ys6_translation_workspace.py`
- 추가: `/tools/scripts/ys6_translation_build.py`
- 추가: `/tools/scripts/tests/test_ys6_translation_workspace.py`
- 갱신: `/docs/plan/018-ys6-translation-workspace-and-batch-build.md`
- 추가: `/docs/result/018-ys6-translation-workspace-and-batch-build.md`
- 생성: `/patched/018-translation-batch-poc/Ys VI - translation-batch-poc.iso`

작업 자료:

- `/.work/ys6-translation-workspace/translations.json`
- `/.work/ys6-translation-workspace/translations.csv`
- `/.work/ys6-translation-workspace/poc-translations.json`
- `/.work/ys6-translation-workspace/batch-report.json`

게임 원본 데이터와 수정 XSO·아카이브는 `/.work`에만 두고 Git에 포함하지 않는다.

## 테스트

- 단위 테스트 50개 통과
- `python -m compileall -q tools` 통과
- 전체 작업공간 7,424개 검증 통과
- 배치 XSO 재파싱 및 교체 바이트 검증 통과
- `.z` CRC32·비압축 크기·payload 왕복 검증 통과
- ISO 내부 파일 재추출 SHA-256 일치
- 원본 대비 허용 범위 밖 변경 0건
- GUI 사용자 편집·저장 확인
- PPSSPP 연속 2개 대사와 후속 이벤트 확인

## 남은 범위와 제약

- 전체 `/data/arc` 목록과 1,194개 카탈로그 XSO의 런타임 대응표는 아직 없다.
- 수정 `.xso.z`가 기존 엔트리 할당을 넘으면 현재 빌드는 중단해야 한다.
- 다음 단계는 ISO의 모든 런타임 아카이브를 읽기 전용으로 열거하고, 내부 엔트리와 standalone XSO를 payload 해시로 대응시키는 작업이 적절하다.
- 그 다음 단계에서 할당 초과 파일을 포함하는 아카이브 전체 재배치를 설계할 수 있다.
