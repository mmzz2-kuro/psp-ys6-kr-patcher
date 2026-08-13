# 036. 기존 번역을 Windows판 한국어 데이터로 교체하는 계획

## 목적

계획 035에서 보존했던 기존 번역 레코드도 Windows판 한국어 패치에서 추출한 문장으로 교체한다.

## 배경

계획 035에서는 안전을 위해 다음 항목을 유지했다.

- 기존 번역 `draft`: 671개
- 사용자 승인 `override`: 142개

Windows판 신규 번역 3,772개만 `draft`로 추가했기 때문에, 현재 작업공간에는 기존 번역과 Windows판 번역이 함께 존재한다.

## 교체 대상 선택

교체 범위는 다음 두 가지로 나뉜다.

### 선택 A: 기존 draft만 교체

- 기존 번역이 입력된 `draft` 671개를 Windows판 문장으로 교체한다.
- `override` 142개는 사용자가 이미 검수한 내용이므로 그대로 유지한다.
- 교체한 레코드는 계속 `draft` 상태로 둔다.

### 선택 B: 기존 draft와 override 모두 교체

- 기존 `draft` 671개와 `override` 142개를 모두 Windows판 문장으로 교체한다.
- 기존 `override` 문장을 바꾸면서 승인 상태를 그대로 유지하면 검수되지 않은 문장이 즉시 패치에 들어가므로 안전하지 않다.
- 따라서 교체한 기존 `override`도 `draft`로 되돌린다.
- 결과적으로 현재 패치에 반영되는 승인 번역 수가 감소하며 다시 사용자 검수가 필요하다.

권장안은 선택 A이다. 기존 `override`는 사용자가 실제 게임에서 확인하거나 승인한 결과이므로 자동 교체하지 않는 편이 안전하다.

## 처리 절차

1. 현재 `/tools/config/dialogue-translations.json`의 SHA-256과 상태별 수량을 기록한다.
2. 교체 전 전체 작업공간을 `.work/ys6-windows-existing-replacement`에 백업한다.
3. 계획 035의 `psp-match-report`에서 Windows판과 `exact` 대응되는 기존 번역만 선택한다.
4. 선택된 범위의 `translation`을 Windows판 문장으로 교체한다.
5. `notes`에 Windows판 교체 출처와 작업 번호 036을 기록한다.
6. 선택 B인 경우 변경된 `override`를 모두 `draft`로 되돌린다.
7. 변경 전후 문장과 상태를 비교 보고서로 저장한다.
8. 번역 작업공간 검증을 실행한다.

## 안전 조건

- Windows판과 PSP판의 경로·인덱스가 `exact`인 레코드만 교체한다.
- `review` 및 `unmatched` 537개는 교체하지 않는다.
- Windows 번역이 비어 있거나 한글이 없는 항목은 교체하지 않는다.
- 원본 ISO와 Windows판 패치 파일은 수정하지 않는다.
- 이번 작업에서는 PSP ISO를 빌드하지 않는다.
- 교체 전 작업공간 전체 백업과 변경 목록을 남긴다.

## 예상 산출물

- 갱신된 `/tools/config/dialogue-translations.json`
- 교체 전 백업 JSON
- 변경 전후 비교 JSON
- 상태 및 검증 요약
- `/docs/result/036-ys6-replace-existing-translations-with-windows-data.md`

## 상태

- 계획 작성 완료
- 사용자 확인 완료: 선택 B, 기존 draft와 override 전체 교체
- 정확 대응 기존 번역 전체 교체 완료
- 결과 문서: `/docs/result/036-ys6-replace-existing-translations-with-windows-data.md`
