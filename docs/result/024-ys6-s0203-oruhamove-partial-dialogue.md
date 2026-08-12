# Ys VI s_0203/OruhaMove 부분 번역 및 한글 자간 보정 결과

## 상태

- 작업 번호: 024
- 구현: 완료
- 정적 검증: 완료
- 인게임 검증: 완료
- 완료일: 2026-08-12

## 결과 요약

`s_0203/OruhaMove`에 사용자가 작성한 부분 번역 12개를 기존 023 누적 번역에 추가했다. 아카이브와 standalone 사본을 함께 수정했으며 PPSSPP에서 한글 출력과 이벤트 진행을 확인했다.

초기 ISO에서는 굴림 글리프마다 좌측 여백이 달라 시각적 자간이 불균일했다. 비교용 격자를 통해 정렬 방식을 검토한 뒤 모든 한글 글리프의 실제 bbox 시작점을 `x=1`로 맞췄다. 사용자가 새 ISO에서 자간이 균일해졌음을 확인했다.

## 번역 적용

- 기존 023 검수 번역: 51개
- 신규 `s_0203/OruhaMove`: 12개
- 최종 검수 번역: 63개
- 신규 인덱스: 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14
- 빈 번역 9개는 제외
- 줄바꿈 및 `\x1` 토큰 검증 통과
- 사용자 번역 정본은 변경하지 않음

## 글리프 자간 보정

- 게임 글리프 셀: 16×12픽셀, 1비트 비트맵
- 굴림 렌더 크기: 12픽셀
- 한글 글리프: 182개
- 보정 전 bbox 왼쪽 시작점: 0–3픽셀
- 보정 후 bbox 왼쪽 시작점: 모두 1픽셀
- 획 폭과 세로 위치는 유지
- 수동 `한` 글리프도 같은 정렬 규칙 적용
- 인게임 안티앨리어싱은 적용하지 않음

확인용 atlas가 뿌옇게 보인 것은 통합 빌더에서 8배 확대 PNG에 기본 보간이 사용된 표시 문제였다. 실제 EBOOT 글리프는 회색 픽셀이 없는 1비트 데이터다. 후속 작업에서는 atlas 확대도 `Image.Resampling.NEAREST`로 통일한다.

## 최종 ISO

- 경로: `/patched/024-s0203-oruhamove-partial/Ys VI - s0203-oruhamove-left-aligned-korean-build.iso`
- SHA-256: `4EF1CE796498A2A271CF7A24AE37E6DCE6199664D138BCEBBEB69E7B748ECDE4`
- EBOOT SHA-256: `0807320BACC31A5A8AE6C25C039612E9F5C1394B03949CBEA649C4D231D45692`

교체 대상은 EBOOT, 아카이브 4개, standalone 3개로 총 8개다.

## 검증 결과

- XSO 5개 처리
- 아카이브 4개 처리
- standalone 3개 처리
- 모든 압축 결과가 기존 할당 이내
- 허용 extent 밖 변경 0건
- 자동 테스트 77개 통과
- Python 바이트코드 컴파일 통과
- 원본 ISO SHA-256 유지
- 기존 023 및 최초 024 ISO 보존

사용자 인게임 확인:

- 신규 오르하 대사 12개 한글 정상 출력
- 이벤트 정상 진행
- 왼쪽 정렬 적용 후 자간 균일화 확인

## 생성·변경 파일

- 수정: `/tools/scripts/ys6_hangul_font_build.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 수정: `/tools/scripts/ys6_translation_workspace.py`
- 추가: `/tools/scripts/ys6_glyph_atlas_grid.py`
- 추가·수정: 관련 자동 테스트
- 생성: `/.work/ys6-s0203-oruhamove-partial`
- 생성: `/.work/ys6-s0203-oruhamove-left-aligned`
- 생성: 최종 024 ISO

## 정리 대상

아래 파일은 비교 또는 중간 검증본이며 최종본이 아니다. 추적 가능성을 위해 현재는 삭제하지 않았다.

- `/patched/024-s0203-oruhamove-partial/Ys VI - s0203-oruhamove-partial-korean-build.iso`
- `/.work/ys6-s0203-oruhamove-partial/alignment-preview`
- `/.work/ys6-s0203-oruhamove-partial/left-align-preview`

## 후속 작업

번역 작업공간에 아직 적용되지 않은 번역은 19개 경로, 22개다.

- `s_0000/talkkebin`: 3개
- `s_0000/talktokusa`: 2개
- `s_hidden1` 인물명 XSO: 17개

다음 단계에서는 먼저 `talkkebin`과 `talktokusa`의 실제 런타임 변형을 확정하고 5개 번역을 적용한다. `s_hidden1` 인물명은 구조 변형 대응이 필요하므로 별도 단계로 분리한다.
