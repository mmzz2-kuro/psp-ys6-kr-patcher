# 036. 기존 번역의 Windows판 한국어 데이터 전체 교체 결과

## 결과

사용자가 선택한 전체 교체 방식에 따라 기존 번역이 있던 레코드도 Windows판 한국어 패치 문장으로 교체했다.

- Windows판과 PSP판이 정확히 대응하는 기존 번역: 4,585개 교체
- 실제 문장 내용이 달라진 레코드: 741개
- 이미 같은 Windows 문장이던 레코드: 3,844개
- 기존 `override`: 142개 전부 `draft`로 전환
- 최종 `override`: 0개
- 최종 번역 포함 `draft`: 4,628개
- 작업공간 레코드: 7,424개, 변경 없음

교체한 레코드는 모두 `draft`이며 다음 메모를 기록했다.

`Windows 한국어 패치 전체 번역 교체; 재검수 필요 (issue 036)`

## 적용 기준

다음 조건을 모두 만족하는 기존 번역을 교체했다.

1. Windows판과 PSP판의 XSO 경로가 대응한다.
2. XSO 문자열 수와 문자열 인덱스가 정확히 일치한다.
3. 역할이 대사, 선택지, 선택지 질문 또는 화자 문자열이다.
4. Windows판 문자열이 비어 있지 않다.

한글 없이 말줄임표만 있던 기존 `override` 2개도 전체 교체 범위에 포함했다. 따라서 사용자 승인 상태가 남아 있지 않다.

## 자동 교체하지 않은 기존 번역

기존 번역 중 43개는 정확 대응 조건을 충족하지 않아 보존했다.

- Windows/PSP 구조가 다른 `review` 항목
- PSP에서 경로 또는 인덱스를 찾지 못한 항목
- 대사 이외의 리소스 역할

이 항목까지 인덱스만 보고 교체하면 다른 문장이나 리소스를 덮어쓸 수 있으므로 전체 교체 요청에서도 안전 조건을 유지했다. 해당 항목은 비교·대응 보고서에서 별도로 검토할 수 있다.

## 백업 및 비교 자료

- 교체 전 전체 작업공간:
  - `.work/ys6-windows-existing-replacement/dialogue-translations.before.json`
  - SHA-256: `7494B5E67729C14718DBF0002FDCF608D9DD7E123A21329BC0DBD513320046A3`
- 1차 교체 비교:
  - `.work/ys6-windows-existing-replacement/comparison.json`
- 말줄임표 예외 보정 전 백업:
  - `.work/ys6-windows-existing-replacement/dialogue-translations.after-first-pass.json`
- 최종 보정 비교:
  - `.work/ys6-windows-existing-replacement/comparison-final-pass.json`
- 최종 작업공간 SHA-256:
  - `779644D68F6AB7948365323E7C9642A87BD003051545BE522A26AFD48711498E`

## 검증

- `ys6_translation_workspace.py validate`: `valid=true`
- 검증 오류: 0건
- 경고: 4,628건
  - 번역이 들어 있는 모든 `draft`를 알리는 기존 검증기의 의도된 경고이다.
- 레코드 수: 적용 전후 7,424개
- `override`: 142개에서 0개로 전환 확인
- 원본 ISO 및 Windows 패치 파일은 수정하지 않음
- PSP ISO 빌드는 수행하지 않음

## 변경 파일

- `/tools/config/dialogue-translations.json`
- `/tools/scripts/ys6_windows_dialogue_match.py`
- `/docs/plan/036-ys6-replace-existing-translations-with-windows-data.md`
- `/docs/result/036-ys6-replace-existing-translations-with-windows-data.md`

## 다음 단계

전체 번역이 다시 `draft` 상태이므로 GUI에서 Windows판 문장을 검수하고 승인할 항목을 `override`로 전환해야 한다. 패치 빌드에는 `override`만 들어가므로 현재 상태에서 빌드하면 대사 번역이 반영되지 않는다.

## 상태

- 정확 대응 기존 번역 전체 교체 완료
- 기존 override 전체 draft 전환 완료
- 작업공간 검증 완료
