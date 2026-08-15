# 050. Ys VI EBOOT 시스템 메시지 추출·편집·패치 결과

## 결과

EBOOT에 EUC-JP로 저장된 시스템 메시지를 추출하고 GUI에서 편집한 뒤 기존 통합 빌드에 적용할 수 있도록 구현했다. 기본 작업공간에는 260개 후보가 들어 있으며, 안전을 위해 모두 `untranslated` 상태로 생성했다. 사용자가 번역을 입력하고 `override`로 변경한 항목만 패치에 포함된다.

## 구현 내용

### 시스템 메시지 작업공간

- 신규 스크립트: `/tools/scripts/ys6_system_message_workspace.py`
- 신규 기본 데이터: `/tools/config/system-messages.json`
- 저장 인코딩: EUC-JP
- 상태: `untranslated`, `draft`, `override`, `excluded`, `conflict`
- 원본 EBOOT SHA-256, 문자열 오프셋, 원본 바이트, 문자열별 SHA-256 및 할당 길이를 검증한다.
- 원본 공간보다 긴 `override` 번역은 자동 절단하지 않고 오류로 차단한다.
- 패치는 고정 길이 제자리 교체 방식이며 남는 공간은 0 바이트로 종료·정리한다.

기준 문구 `装備全般の設定を行います。`는 다음과 같이 추출됐다.

- 식별자: `SYS_0012CF34`
- EBOOT 오프셋: `0x12CF34`
- 할당 크기: 27바이트(종료 바이트 포함)

### GUI

`/tools/ys6_dialogue_viewer.py`에 `시스템 메시지` 탭을 추가했다.

- 프로그램 실행 시 기본 JSON 자동 로드
- 원문·번역·오프셋·분류·메모 검색
- 상태 필터
- 다중 선택 후 일괄 `override`
- 번역 바이트 길이 표시
- 길이 초과 항목을 `conflict`로 변경
- 미저장 변경이 있으면 패치 빌드 전에 함께 저장

### 통합 빌드

`/tools/scripts/ys6_patch_builder.py`와 `/tools/scripts/ys6_integrated_build.py`를 확장했다.

- 시스템 메시지 JSON을 필수 패치 데이터로 검사
- `override` 번역 문자를 EBOOT 한글 글리프 매핑 생성에 포함
- 원본 EBOOT 문자열을 먼저 패치한 뒤 기존 폰트 패치를 적용
- `system-message-report.csv` 생성
- preflight 요약과 build manifest에 적용 수, 입력 경로 및 SHA-256 기록
- 기존 대사·인물명·아이템·몬스터명 빌드 흐름 유지

## 검증 결과

### 추출 검증

- 원본 복호화 EBOOT 후보: 260개
- 기준 문구 검출: 성공
- 기준 오프셋 `0x12CF34`: 일치

### 패치 단위검증

기준 문구를 테스트 번역 `장비 설정을 합니다.`로 메모리상 패치했다.

- 할당 크기: 27바이트
- 번역 인코딩 및 종료 포함 길이: 21바이트
- 폰트 빌드 후 해당 오프셋에 번역 바이트 유지: 성공
- 실제 기본 JSON은 변경하지 않았으며 기준 문구 상태는 `untranslated`다.

### 역테스트

- 100자의 한글을 9바이트 공간에 넣은 테스트: 길이 초과 오류 발생 확인
- 원본 바이트 및 EBOOT 해시 불일치 검사 구현

### 전체 검증

- Python 구문 검사: 통과
- `git diff --check`: 오류 없음
- 전체 패치 preflight: 통과

```text
valid: true
dialogue override: 4665
xso: 463
archives: 49
standalone: 450
cast names: 58
items: 72
system messages applied: 0
glyphs: 967
overflow: 0
```

시스템 메시지 적용 수가 0인 것은 기본 작업공간의 모든 항목을 의도적으로 미승인 상태로 생성했기 때문이다.

## 생성·변경 파일

- `/tools/scripts/ys6_system_message_workspace.py`
- `/tools/config/system-messages.json`
- `/tools/ys6_dialogue_viewer.py`
- `/tools/scripts/ys6_patch_builder.py`
- `/tools/scripts/ys6_integrated_build.py`
- `/docs/plan/050-ys6-eboot-system-message-editor.md`
- `/docs/result/050-ys6-eboot-system-message-editor.md`

## 알려진 제한

- 자동 추출된 260개는 EUC-JP 문자열 후보이므로 실제 화면 용도는 사용자가 확인하며 분류해야 한다.
- 원본 할당 공간을 초과하는 번역은 현재 적용할 수 없다. 문자열 재배치와 포인터 수정은 별도 작업이 필요하다.
- 메뉴 이미지에 포함된 글자는 이 작업공간의 대상이 아니다.

## ROM 처리

- 원본 ISO는 수정하지 않았다.
- 새 ISO를 생성하지 않았다.
- `/tools/patchdata/work/current`에서 preflight 산출물만 갱신했다.
