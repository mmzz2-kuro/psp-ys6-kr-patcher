# 084. Ys VI GUI 인물·몬스터명 상태 초기화 문제 진단 결과

## 결론

- 증상을 재현했다.
- 원인은 동일 원문이나 공유 payload 충돌이 아니다.
- 인물과 몬스터가 공용으로 사용하는 `CastNameEditor`의 선택 상태 관리 오류다.
- `선택 항목 reviewed` 실행 후 목록을 새로 그리지만, 현재 선택 식별자와 우측 편집 필드는 이전 값으로 남는다.
- 다음 항목을 클릭할 때 이전 편집 필드가 다시 저장되면서 방금 변경한 상태가 `untranslated`로 되돌아간다.

사용자가 표현한 `override`는 이 편집기에서 실제로는 `reviewed` 상태다. 인물·몬스터 작업공간의 유효 상태에는 `override`가 없고 `reviewed`가 패치 적용 상태로 사용된다.

## 문제 흐름

1. 번역은 있지만 상태가 `untranslated`인 항목을 선택한다.
2. 우측 편집 필드에도 `untranslated`가 들어 있다.
3. `선택 항목 reviewed` 버튼을 누른다.
4. 작업공간의 행 상태는 `reviewed`로 변경된다.
5. `refresh()`가 트리를 전부 다시 생성하면서 선택 표시가 사라진다.
6. 그러나 `_selected_identifier`와 우측 `edit_status`는 초기화 또는 재로딩되지 않는다.
7. 다음 행을 클릭하면 `show()`가 이전 식별자에 대해 `_commit_selected()`를 호출한다.
8. 우측에 남아 있던 `untranslated`가 이전 행에 다시 기록된다.
9. 결과적으로 사용자가 방금 `reviewed`로 만든 항목이 `untranslated`로 되돌아간다.

다중 선택인 경우에는 첫 선택 행과 현재 편집 행이 다를 수 있어 사용자가 보기에 다른 항목이 바뀐 것처럼 나타날 가능성도 있다.

## 재현 사례

현재 실제 작업공간은 수정하지 않고 메모리 복사본에서 다음 항목으로 재현했다.

| 구분 | 식별자 | 시작 상태 | 버튼 직후 | 다음 행 선택 후 |
|---|---|---|---|---|
| 인물 | `CAST_C920` | `untranslated` | `reviewed` | `untranslated` |
| 몬스터 | `CAST_M450` | `untranslated` | `reviewed` | `untranslated` |

두 경우 모두 번역 문자열이나 메모는 변하지 않고 상태만 되돌아갔다.

## 실제 작업공간 현황

- 경로: `tools/config/cast-names.json`
- 전체 항목: 164개
- `reviewed`: 67개
- `untranslated`: 97개
- 인물: `reviewed` 60개, `untranslated` 28개
- 몬스터: `reviewed` 7개, `untranslated` 69개
- 번역이 있지만 `untranslated`인 항목: 인물 4개, 몬스터 4개

마지막 8개는 이 문제로 되돌아간 항목일 가능성이 있지만, 진단만으로 기존 상태 변경 이력을 확정할 수는 없다.

## 원인 코드

- `CastNameEditor.review_selected()`
  - 선택 행의 상태를 `reviewed`로 변경한 뒤 `self.refresh()`만 호출한다.
  - 갱신된 항목을 다시 선택하거나 편집 필드를 갱신하지 않는다.
- `CastNameEditor.refresh()`
  - 트리 행을 삭제하고 다시 만들지만 `_selected_identifier`를 정리하지 않는다.
- `CastNameEditor.show()`
  - 새 행을 표시하기 전에 남아 있는 `_selected_identifier`에 `_commit_selected()`를 호출한다.
- `CastNameEditor._commit_selected()`
  - 오래된 우측 필드의 상태를 해당 식별자 행에 다시 기록한다.

## 배제된 원인

- 식별자 중복: 없음. 검증기가 중복 식별자를 오류로 처리한다.
- 동일 원문 충돌: 동일 원문 그룹은 존재하지만 편집기 저장 키는 원문이 아니라 고유 `identifier`다.
- 인물과 몬스터 payload 충돌: 두 분류는 같은 JSON을 사용하지만 식별자가 분리돼 있으며 일괄 동기화 코드가 없다.
- 필터 인덱스 불일치: 트리 인덱스는 현재 `filtered` 목록에 맞춰 다시 생성되므로 이번 증상의 직접 원인이 아니다.
- 저장 파일 재생성: `save()`는 현재 작업공간을 원자적으로 기록할 뿐 다른 행 상태를 기본값으로 재생성하지 않는다.

## 권장 수정 방향

1. `review_selected()`에서 현재 편집 내용을 먼저 커밋한다.
2. 변경 후 선택을 유지할 대표 식별자를 저장한다.
3. `refresh(select=대표 식별자)`로 갱신된 실제 상태를 우측 필드에 다시 로딩한다.
4. 선택을 유지하지 않을 경우 `_selected_identifier = None`으로 초기화하고 편집 필드도 비운다.
5. 다중 선택에서는 변경 대상 식별자 목록으로 행을 다시 선택하되, 우측 편집 기준은 명확히 한 행으로 제한한다.
6. `open()`에서도 이전 파일의 `_selected_identifier`가 남지 않게 초기화한다.

## 필요한 회귀 테스트

- 인물 한 항목을 `reviewed`로 바꾼 뒤 다른 행 선택 시 상태 유지
- 몬스터 한 항목에서 동일 검증
- 인물·몬스터 다중 선택 상태 변경 후 모든 대상 유지
- 상태 필터가 `untranslated`일 때 변경된 행이 목록에서 사라져도 상태 유지
- 검색 필터 적용 중 변경 후 원본 식별자에 정확히 반영
- 다른 작업공간을 다시 열었을 때 이전 선택 식별자 미사용
- 저장·재로드 후 변경 대상 외 상태 및 번역 불변

## 변경 및 보존 사항

- 생성: `docs/result/084-ys6-cast-monster-status-reset-diagnosis.md`
- 완료 갱신: `docs/plan/084-ys6-cast-monster-status-reset-diagnosis.md`
- GUI 코드와 실제 `tools/config/cast-names.json`은 수정하지 않았다.
- 원본 ISO와 패치 ISO는 사용하거나 변경하지 않았다.
