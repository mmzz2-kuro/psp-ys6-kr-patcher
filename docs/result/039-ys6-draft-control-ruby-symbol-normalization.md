# 039. 전체 draft 제어문자·루비·특수문자 정규화 결과

## 결과

계획 039의 1~4번 범위를 번역 작업공간에 적용했다. 모든 레코드는 `draft` 상태를 유지했으며 실제 override 승격이나 ISO 빌드는 수행하지 않았다.

## 수행 내용

### 플레이어명

- 원문의 `\x1`이 번역에서 고정 이름 `아돌`로 확장된 258개 레코드에 `allow_player_name_expansion`을 설정했다.
- 검증기는 해당 필드가 있을 때만 `\x1`과 `아돌`의 제한적인 차이를 허용한다.
- `\n`, `\x3`, `\x4` 등 다른 제어 토큰 차이는 계속 오류로 취급한다.

### 백슬래시와 제어문자

- 단독 백슬래시 12개를 원문의 줄바꿈 수와 일치하는 경우에 한해 `\n`으로 자동 교정했다.
- 자동 판정이 어려웠던 3개는 원문 문맥을 대조하여 개별 교정했다.
- 플레이어명 확장과 다른 줄바꿈 오류가 함께 있던 3개도 개별 교정했다.
- 문맥 교정은 총 6개다.

### 루비

- 일본어 독음용 `<ruby:...>...<endruby>`만 제거된 136개 레코드에 `allow_markup_change`를 설정했다.
- 색상 및 크기 태그가 함께 달라진 항목은 자동 허용하지 않는 판정 규칙을 추가했다.
- 이번 136개는 모두 순수 루비 제거 조건을 충족했다.

### 특수문자 후보군

- 미지원 문자 53회를 기존 지원 문자 후보로 치환했다.
- 세부 후보와 변경 가능 정책은 `/docs/result/039-ys6-special-character-candidate-policy.md`에 별도로 기록했다.
- `《 》`의 최초 후보였던 `< >`는 마크업 충돌 가능성 때문에 `[ ]`로 변경했다.
- `ㆍ`의 최초 후보였던 `·`는 새 글리프가 필요하므로 `.`으로 변경했다.

## 변경 파일

- `/tools/config/dialogue-translations.json`
- `/tools/scripts/ys6_translation_workspace.py`
- `/tools/scripts/ys6_draft_normalize.py`
- `/docs/plan/039-ys6-draft-control-ruby-symbol-normalization.md`
- `/docs/result/039-ys6-special-character-candidate-policy.md`
- `/docs/result/039-ys6-draft-control-ruby-symbol-normalization.md`

## 검증 결과

- 작업공간 레코드: 7,424개
- draft: 4,628개
- override: 0개
- 실제 작업공간 검증: 통과
- 정규화 변경 레코드: 431개
- 자동 또는 개별 판정 보류: 0개
- 적용 후 SHA-256: `260174E9E5E2C42FA14EE3602C3FD024501521CA81C88C73C157D50CD59283F2`
- 원본 백업 SHA-256: `779644D68F6AB7948365323E7C9642A87BD003051545BE522A26AFD48711498E`

전체 draft를 복사본에서 가상 override로 승격했을 때 검증 오류는 기존 406개에서 40개로 감소했다. 남은 40개는 이번 허용 범위에 포함되지 않은 다른 제어 토큰 불일치이며 계속 차단된다. 마크업 불일치는 0개다.

## 백업 및 보고서

- 변경 전 백업: `/.work/ys6-draft-normalization/dialogue-translations.before.json`
- 미리보기: `/.work/ys6-draft-normalization/preview.json`
- 변경 상세: `/.work/ys6-draft-normalization/normalization-report.json`
- 가상 승격본: `/.work/ys6-draft-normalization/all-drafts-override.json`

## 보류 사항

- 남은 제어 토큰 불일치 40개
- 공유 payload 번역 충돌 66그룹
- many-to-many `ridepedestal` 대응
- Windows/PSP 비정확 대응 43개 검수
- 긴 문장 26개 화면 폭 교정
- 전체 draft의 실제 override 전환
- 패치 ISO 빌드 및 게임 화면 검증

## ROM 처리

- 원본 ISO는 읽거나 수정하지 않았다.
- 새 패치 ISO 또는 테스트 ISO를 생성하지 않았다.
- 삭제할 임시 ROM은 없다.
