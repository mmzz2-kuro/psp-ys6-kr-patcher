# 037. Ys VI 대사 GUI 다중 선택 override 기능 결과

## 결과

`/tools/ys6_dialogue_viewer.py` 대사 탭에 `선택 항목 override` 버튼을 추가했다.

- 한 행을 선택하고 누르면 해당 항목을 `override`로 변경한다.
- `Ctrl+클릭`으로 여러 행을 선택하거나 `Shift+클릭`으로 범위를 선택한 뒤 누르면 선택한 항목을 모두 처리한다.
- 번역문과 메모는 변경하지 않고 상태만 바꾼다.
- 이미 `override`인 항목은 그대로 유지한다.
- 번역문이 비어 있는 항목은 건너뛴다.
- 처리 후 선택 상태를 유지하고 목록의 상태 열을 즉시 갱신한다.
- 상태 필터가 활성화된 경우 변경된 조건에 맞춰 목록을 다시 표시한다.
- 결과는 상태 표시줄에 변경, 기존 override 및 빈 번역 제외 수량으로 표시한다.

## 사용 방법

1. `/tools/ys6_dialogue_viewer.py`를 실행한다.
2. 대사 탭에서 승인할 행을 선택한다.
3. 여러 항목은 `Ctrl+클릭` 또는 `Shift+클릭`으로 선택한다.
4. `선택 항목 override` 버튼을 누른다.
5. 상단 `번역 저장`을 눌러 JSON 파일에 저장한다.

버튼을 누른 것만으로는 디스크에 즉시 저장하지 않는다. 기존 GUI의 미저장 변경 정책을 유지한다.

## 구현 내용

### `mark_records_override`

테스트 가능한 순수 함수로 배치 상태 변경을 분리했다.

- 입력 레코드 수 집계
- 변경된 레코드 수 집계
- 이미 override인 레코드 수 집계
- 빈 번역 제외 수 집계
- 번역문·메모 무변경 보장

### GUI 연계

- 대사 `Treeview`에 `selectmode="extended"` 명시
- 편집 영역에 `선택 항목 override` 버튼 배치
- 선택 행을 `self.filtered`의 레코드와 연결해 일괄 처리
- 실제 변경이 있으면 `dialogue_dirty = True`
- 상태 필터가 없을 때는 행을 제자리 갱신하여 선택 유지
- 필터가 있을 때는 목록 재구성

## 검증 결과

### 순수 함수 시험

다음 네 레코드를 함께 처리했다.

- `draft` 번역 1개
- `untranslated` 상태지만 번역이 있는 항목 1개
- 기존 `override` 1개
- 빈 번역 `draft` 1개

결과:

- 변경: 2개
- 기존 override: 1개
- 빈 번역 제외: 1개
- 최종 상태: `override`, `override`, `override`, `draft`
- 번역문과 메모 변경 없음

### GUI 스모크 시험

- GUI 기본 작업공간 로딩 성공
- 대사 탭 생성 성공
- Treeview `extended` 선택 모드 확인
- `선택 항목 override` 버튼 생성 확인
- 실제 Treeview의 세 행 다중 선택 처리 성공
- 번역이 있는 두 행 override 변경 확인
- 빈 번역 한 행 제외 확인
- 다중 선택 유지 확인
- 미저장 변경 상태 확인

### 정적 검증

- `python -m py_compile tools/ys6_dialogue_viewer.py`: 통과
- `git diff --check`: 통과

## 변경 파일

- `/tools/ys6_dialogue_viewer.py`
- `/docs/plan/037-ys6-gui-batch-override-action.md`
- `/docs/result/037-ys6-gui-batch-override-action.md`

## 데이터 영향

- 검증 과정에서 실제 `/tools/config/dialogue-translations.json`을 저장하거나 변경하지 않았다.
- PSP ISO를 빌드하거나 수정하지 않았다.

## 상태

- 구현 완료
- 다중 선택 및 배치 override 검증 완료
