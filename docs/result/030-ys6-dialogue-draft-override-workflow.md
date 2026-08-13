# Ys VI 대사 초벌 번역·override 승인 흐름 전환 결과

## 상태

- 작업 번호: 030
- 상태 체계 구현: 완료
- 기존 번역 이관: 완료
- 첫 dialogue 초벌 번역: 완료
- 자동 검증: 완료
- 사용자 초벌 번역 검토: 대기
- ISO 생성: 수행하지 않음
- 작업일: 2026-08-13

## 결과 요약

대사 번역 흐름을 다음과 같이 변경했다.

```text
untranslated → Codex 초벌 번역(draft) → 사용자 승인(override) → 패치 적용
```

통합 빌더는 대사 작업공간에서 `override`만 선택한다. 번역문이 존재하더라도 `draft` 상태이면 글리프 생성과 XSO 패치에서 제외된다. 인물명 작업공간은 변경하지 않았으며 기존처럼 `reviewed`만 적용한다.

## 전체 작업공간 이관

`/tools/config/dialogue-translations.json`을 전체 카탈로그와 동기화했다.

- 전체 레코드: 7,424개
- 기존 승인 번역: 115개 → 모두 `override`
- Codex 초벌 번역: 23개 → 모두 `draft`
- 사용자 승인 번역: 138개 → `override`
- 미번역: 7,263개

기존 115개는 상태를 제외한 모든 필드가 이관 전과 동일하다. 루비 제거가 승인된 3개 항목의 `allow_markup_change`도 보존했다.

이관 전 백업:

- `/tools/config/dialogue-translations.pre-override.json`

## 첫 dialogue 초벌 번역

첫 묶음은 `s_0200`의 연속된 생활 대화 3개 XSO로 제한했다.

- `talkisha.xso.z`: 7개
- `talkisha0.xso.z`: 5개
- `talkolha0.xso.z`: 6개
- 합계: 18개

내용은 이샤의 걱정, 축제 준비, 카나안섬에서 돌아온 아돌을 맞는 오르하의 대화다. 모든 번역은 `draft`이며 사용자가 승인하기 전에는 패치에 포함되지 않는다.

초벌 정본 및 원문 SHA:

- `/.work/ys6-dialogue-draft-override/batch-030-s0200.json`

## GUI 변경

- 대사 상태에 `override` 추가
- 신규 `reviewed` 선택 제거
- 상태 필터 추가:
  - 전체
  - dialogue
  - draft
  - override
  - untranslated
  - excluded/conflict/orphaned
- 목록에 상태 열 추가
- 전체 7,424개 기본 자동 로드
- 사용자가 draft 번역을 교정한 후 override로 전환 가능

## 안전 검증

- draft 적용 시 대상이 반드시 `dialogue`인지 확인
- `(iso_path, string_index)` 존재 여부 확인
- 원문 SHA-256 확인
- 중복 초벌 키 차단
- 빈 초벌 번역 차단
- 제어 토큰 손실 차단
- 마크업 손실·변경 차단
- override 항목을 초벌 번역이 덮어쓰는 동작 차단

## 빌드 회귀 검증

전체 작업공간으로 통합 빌더 preflight를 실행했다.

- 선택된 override: 115개
- 제외된 draft: 18개
- 인물명 reviewed: 14개
- 글리프: 198개
- 할당 초과: 0건
- EBOOT SHA-256: 029 결과와 동일
  - `DF3DACC39574C8B40BD3A7ACD94061EF2D566FB610F97E4D1BBF29DE36DCA679`
- `castinfo.dat` SHA-256: 029 결과와 동일
  - `51D865AD03F54D539E382F4E74811627875C7850BE7BADD5B7A9F2A72DBF59CC`

따라서 18개 초벌 번역은 아직 패치 결과에 영향을 주지 않는다.

## 코드 검증

- Python 컴파일 통과
- 자동 테스트 91개 통과
- 작업공간 검증 통과
- 신규 draft 병합 및 토큰 손실 역테스트 통과

## 변경 파일

- 수정: `/tools/scripts/ys6_translation_workspace.py`
- 수정: `/tools/scripts/ys6_translation_resolver.py`
- 수정: `/tools/scripts/ys6_integrated_build.py`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정: `/tools/scripts/tests`
- 수정: `/tools/config/dialogue-translations.json`
- 생성: `/tools/config/dialogue-translations.pre-override.json`
- 생성: `/.work/ys6-dialogue-draft-override/batch-030-s0200.json`

## 사용자 검토 방법

1. `python tools/ys6_dialogue_viewer.py` 실행
2. 대사 탭의 상태 필터에서 `draft` 선택
3. 표시되는 18개 번역 검토
4. 필요한 문장을 교정
5. 패치에 넣을 항목의 상태를 `override`로 변경
6. 저장

사용자 검토가 끝난 뒤 별도 계획에서 승인된 override만 새 ISO에 적용한다.

## 추가 초벌 번역: `s_020a/adolsleep`

사용자가 즉시 접근 가능한 `s_020a/adolsleep.xso.z`를 요청하여, 기존 override를 건드리지 않고 미승인 dialogue 29~33번 5개를 추가로 번역했다.

- 29: 오르하야, 부디 잊지 말거라.
- 30: 정령신 알마의 후예인 무녀로서의 본분을.
- 31: 저기, 죄송해요. / 큰아버지께 악의가 있는 건 아니에요.
- 32: 다만 요즘 에레시아 사람들에게 / 조금 완고해지셔서……
- 33: ……아무튼 지금은 / 편히 쉬세요.

30·32번은 일본어 발음용 ruby 제거를 명시적으로 허용했다. 초벌 파일은 다음 경로에 보존했다.

- `/.work/ys6-dialogue-draft-override/batch-030-adolsleep.json`

GUI에서 입력한 실제 개행이 게임의 `\\n` 제어 토큰과 달라지는 문제도 발견해, 대사 저장 시 실제 개행을 게임 토큰으로 정규화하도록 수정했다. 기존 사용자 번역은 내용 변경 없이 줄바꿈 표현만 정규화했으며 변경 전 파일을 다음 경로에 백업했다.

- `/tools/config/dialogue-translations.pre-newline-normalization.json`

추가 검증 후 자동 테스트는 92개가 통과했다.
