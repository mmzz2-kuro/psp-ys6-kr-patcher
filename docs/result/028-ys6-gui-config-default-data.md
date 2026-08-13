# Ys VI GUI 기본 번역 데이터 `/tools/config` 배치 결과

## 상태

- 작업 번호: 028
- 구현: 완료
- 자동 검증: 완료
- 사용자 GUI 실행 확인: 대기
- 완료일: 2026-08-13

## 결과

사용자용 GUI의 기본 번역 데이터를 개발 중간 경로인 `/.work`에서 `/tools/config`로 이관했다. GUI는 현재 작업 디렉터리가 아니라 `ys6_dialogue_viewer.py`의 실제 위치를 기준으로 설정 경로를 계산한다.

실행 시 대사 번역 작업공간과 인물명 작업공간을 자동으로 연다. 명령행에 JSON 경로가 지정되면 해당 대사 JSON을 우선하며, 기존 수동 열기 기능은 유지한다.

## 설정 파일

- `/tools/config/dialogue-translations.json`
  - 대사 115개, reviewed 115개
- `/tools/config/cast-names.json`
  - 인물명 164개, reviewed 1개
  - `CAST_C240`: `이샤`, reviewed 유지
- `/tools/config/dialogue-catalog.json`
  - 전체 대사 원문 및 참조 카탈로그

세 파일은 이관 원본과 각각 SHA-256이 동일하다. 기존 `/.work` 파일은 수정하거나 삭제하지 않았다.

## GUI 변경

- 기본 대사 번역 JSON 자동 로드
- 기본 인물명 JSON 자동 로드
- GUI 파일 기준 상대 경로 사용
- 대사 카탈로그와 번역 작업공간 JSON 형식 자동 판별
- 기본 파일 누락 시 앱을 종료하지 않고 상태 메시지 표시
- 대사 저장 시 UTF-8 원자적 교체 및 `.bak` 백업
- 인물명 기존 원자적 저장 및 백업 유지
- 수동 JSON 열기와 CSV 기능 유지

## 검증

- Python 컴파일 통과
- 자동 테스트 88개 통과
- 직접 실행 형태의 모듈 import 통과
- 계산된 기본 경로가 모두 `/tools/config`를 가리킴
- 대사 레코드 및 reviewed 수 일치
- 인물명 164개와 이샤 번역 상태 유지
- 원본 ISO 및 패치 ISO 변경 없음

## 변경 파일

- 생성: `/tools/config/dialogue-translations.json`
- 생성: `/tools/config/cast-names.json`
- 생성: `/tools/config/dialogue-catalog.json`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정: `/tools/scripts/tests/test_ys6_dialogue_extract.py`
- 결과 문서: `/docs/result/028-ys6-gui-config-default-data.md`

## 사용자 확인 항목

`python tools/ys6_dialogue_viewer.py` 실행 직후 다음을 확인한다.

- 대사 탭에 115개가 자동 표시됨
- 인물명 탭에 164개가 자동 표시됨
- 인물명에서 `CAST_C240` 검색 시 `이샤`가 표시됨
