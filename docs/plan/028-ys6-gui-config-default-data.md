# Ys VI GUI 기본 번역 데이터 `/tools/config` 배치 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- 구현: 완료
- 자동 검증: 완료
- 사용자 GUI 확인: 대기
- 결과 문서: `/docs/result/028-ys6-gui-config-default-data.md`

## 배경

현재 `tools/ys6_dialogue_viewer.py`는 실행 시 `/.work/ys6-full-dialogue/catalog/dialogue_catalog.json`만 선택적으로 연다. 실제 대사 번역 작업공간과 인물명 작업공간은 사용자가 매번 파일 선택 창에서 직접 열어야 한다.

`/.work`는 분석·빌드 중간 산출물 경로이므로 사용자용 GUI의 기본 데이터 위치로 적합하지 않다. GUI와 함께 사용할 번역 정본을 `/tools/config`에 배치하고, GUI가 실행 위치와 관계없이 자신의 경로를 기준으로 자동 로드하도록 변경한다.

## 목표

1. GUI 편집에 필요한 JSON 정본을 `/tools/config`에 배치한다.
2. GUI 실행 시 대사 번역과 인물명 번역 데이터를 자동으로 연다.
3. PowerShell 현재 디렉터리와 관계없이 동일하게 동작하게 한다.
4. 기존 수동 파일 열기 기능은 유지한다.
5. 기존 번역 내용과 인물명 164개를 손실 없이 이관한다.

## 기본 파일 구성

다음 이름으로 정리한다.

- `/tools/config/dialogue-translations.json`
  - 현재 누적 대사 번역 정본 `/.work/ys6-remaining-translations-batch-isha-hidden/reviewed-translations.json` 이관
- `/tools/config/cast-names.json`
  - 현재 인물명 정본 `/.work/ys6-translation-workspace/cast-names.json` 이관
- `/tools/config/dialogue-catalog.json`
  - 전체 대사 원문과 참조 정보를 확인할 때 사용하는 카탈로그 이관

GUI 기본 편집 데이터는 `dialogue-translations.json`과 `cast-names.json`이다. `dialogue-catalog.json`은 전체 원문 탐색 및 새 작업공간 동기화를 위한 보조 데이터로 보존하되 기본 대사 탭에는 번역 작업공간을 우선 표시한다.

글리프 매핑, 폰트 사용량, 런타임 아카이브 맵처럼 현재 GUI가 직접 읽지 않는 빌드 전용 JSON은 이번 단계에서 `/tools/config`로 복사하지 않는다. 후속 패치 빌드 GUI에서 필요해질 때 별도 계획으로 배치한다.

## 구현 내용

### 1. 설정 경로

GUI 파일 위치를 기준으로 경로를 계산한다.

```text
tools/ys6_dialogue_viewer.py
tools/config/dialogue-translations.json
tools/config/cast-names.json
tools/config/dialogue-catalog.json
```

현재 작업 디렉터리나 절대 개발 경로를 코드에 넣지 않는다.

### 2. 자동 로드

GUI 시작 시 다음 순서로 처리한다.

1. 명령행에 별도 대사 JSON이 지정되면 해당 파일 우선
2. 별도 지정이 없으면 `/tools/config/dialogue-translations.json` 자동 로드
3. `/tools/config/cast-names.json`이 있으면 인물명 탭에 자동 로드
4. 파일이 없거나 형식이 잘못되면 앱을 종료하지 않고 상태 표시와 오류 안내

기본 파일이 정상이라면 실행 직후 대사와 인물명 목록이 모두 표시되어야 한다.

### 3. 저장

- 대사 탭의 저장은 기본 `dialogue-translations.json`에 반영한다.
- 인물명 탭의 저장은 기본 `cast-names.json`에 반영한다.
- 인물명은 기존 원자적 저장과 `.bak` 백업을 유지한다.
- 대사 작업공간 저장도 원자적 저장 및 `.bak` 백업으로 맞춘다.
- UTF-8 JSON을 사용하고 PowerShell 출력 인코딩에 의존하지 않는다.

### 4. 기존 기능 유지

- 대사 카탈로그 열기
- 대사 작업공간 열기
- 인물명 작업공간 열기
- JSON 저장
- CSV 가져오기·내보내기
- 검색 및 상태 필터

## 데이터 이관 검증

- 원본과 `/tools/config` 사본의 SHA-256 또는 구조적 내용 일치
- 대사 레코드 수와 reviewed 수 일치
- 인물명 레코드 164개 유지
- `CAST_C240`의 `이샤`, `reviewed` 상태 유지
- 모든 한글 문자열 UTF-8 왕복 확인
- 기존 `/.work` 파일은 삭제하거나 수정하지 않음

## GUI 검증

- 저장소 루트에서 `python tools/ys6_dialogue_viewer.py` 실행 시 자동 로드
- `tools` 디렉터리에서 `python ys6_dialogue_viewer.py` 실행 시 자동 로드
- 다른 현재 디렉터리에서 절대 경로로 실행해도 자동 로드
- 대사 탭에 기본 번역 작업공간 표시
- 인물명 탭에 164개 자동 표시
- 수동으로 다른 파일을 여는 기능 유지
- 저장 후 재실행 시 변경 유지
- 기본 파일 누락·손상 시 앱이 종료되지 않고 오류 표시

## 예상 변경 및 산출물

- 생성: `/tools/config/dialogue-translations.json`
- 생성: `/tools/config/cast-names.json`
- 생성: `/tools/config/dialogue-catalog.json`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정 또는 추가: `/tools/scripts/tests`
- 결과 문서: `/docs/result/028-ys6-gui-config-default-data.md`

## 원본 및 ROM 보호

- 원본 ISO와 패치 ISO는 읽거나 수정하지 않는다.
- 기존 `/.work` 번역 JSON은 보존한다.
- 이번 작업에서는 새 ISO를 만들지 않는다.

## 완료 조건

- GUI용 번역 JSON이 `/tools/config`에 정리된다.
- GUI가 실행 즉시 대사·인물명 기본 데이터를 자동 로드한다.
- 실행 디렉터리에 의존하지 않는다.
- 기존 수동 열기와 편집 기능이 유지된다.
- 대사와 인물명 저장이 안전하게 수행된다.
- 자동 테스트와 Python 컴파일이 통과한다.
- 사용자 GUI 실행 확인 후 결과 문서를 작성한다.

## 중단 및 재확인 조건

- 현재 누적 대사 작업공간이 사용자 의도와 다른 정본으로 확인됨
- `/tools/config`에 빌드 전용 대형 데이터까지 포함해야 함
- 자동 로드가 기존 명령행 파일 우선순위를 깨뜨림
- 데이터 이관 과정에서 레코드 또는 번역 내용이 달라짐
