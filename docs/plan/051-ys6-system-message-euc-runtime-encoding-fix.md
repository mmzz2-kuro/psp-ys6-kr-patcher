# 051. Ys VI 시스템 메시지 EUC-JP 런타임 인코딩 수정

## 상태

- 원인 분석 완료
- 사용자 확인 완료
- 구현 및 검증 완료

## 증상

시스템 메시지 `装備全般の設定を行います。`를 `장비 전체 설정`으로 번역해 적용했으나 화면에는 `걷`, `깔` 및 특수 기호가 출력됐다.

## 확인된 원인

050 구현은 기존 대사 인코더가 반환한 CP932 글리프 코드를 EBOOT의 EUC-JP 문자열 영역에 직접 기록했다. 시스템 메뉴 문자열 처리기는 EBOOT 바이트를 EUC-JP로 읽어 내부 CP932 글리프 코드로 변환하므로, 이미 CP932인 바이트에 변환이 한 번 더 적용됐다.

현재 잘못 기록된 바이트:

```text
97F2 9769 20 97E5 97BE 20 97F0 97CB
```

글리프 매핑 코드와 그 코드가 원래 나타내던 일본어 문자를 EUC-JP로 역변환한 올바른 바이트:

```text
장 97F2(劣) -> CEF4
비 9769(擁) -> CDCA
전 97E5(怜) -> CEE7
체 97BE(寮) -> CEC0
설 97F0(歴) -> CEF2
정 97CB(陵) -> CECD
```

시스템 문자열의 공백 역시 ASCII `20`이 아니라 EUC-JP 전각 공백 `A1A1`로 기록해야 런타임에서 기존 게임 공백 코드 `8140`으로 변환된다.

따라서 `장비 전체 설정`의 예상 EBOOT 바이트는 다음과 같다.

```text
CEF4 CDCA A1A1 CEE7 CEC0 A1A1 CEF2 CECD 00
```

## 수정 계획

### 1. 시스템 메시지 전용 인코더

`/tools/scripts/ys6_system_message_workspace.py`에 시스템 문자열 전용 인코딩 단계를 추가한다.

1. 한글 문자를 기존 `mapping.json`의 CP932 게임 코드에 대응시킨다.
2. 해당 CP932 코드를 원래 일본어 문자로 해석한다.
3. 원래 일본어 문자를 EUC-JP로 인코딩하여 EBOOT에 기록한다.
4. 일반 공백은 EUC-JP 전각 공백 `A1A1`로 변환한다.
5. ASCII와 문장부호는 시스템 문자열에서 실제 런타임 변환 결과가 기존 게임 코드와 일치하도록 명시적으로 처리한다.
6. CP932 코드가 EUC-JP로 역변환되지 않는 매핑은 조용히 기록하지 않고 오류로 차단한다.

### 2. 길이 계산 일치

- GUI의 시스템 메시지 길이 표시와 검증은 전용 EUC-JP 인코더가 생성하는 실제 바이트 길이를 기준으로 한다.
- `override` 전환, 저장 검증, preflight가 모두 동일한 인코더를 사용한다.
- 고정 할당 공간 초과 시 기존처럼 `conflict` 또는 빌드 오류로 처리한다.

### 3. 통합 빌드 수정

- `/tools/scripts/ys6_integrated_build.py`에서 시스템 메시지 패치에 일반 `encode_translation` 결과를 직접 사용하지 않는다.
- 시스템 메시지 전용 인코더를 호출하되 기존 대사·인물명·아이템 인코딩에는 영향을 주지 않는다.
- `system-message-report.csv`에 최종 EBOOT 바이트를 기록한다.

## 검증 계획

1. `장비 전체 설정`이 `CEF4CDCAA1A1CEE7CEC0A1A1CEF2CECD`로 인코딩되는지 확인한다.
2. 각 EUC-JP 바이트를 런타임 변환과 같은 방식으로 CP932로 되돌렸을 때 `97F2 9769 8140 97E5 97BE 8140 97F0 97CB`가 되는지 확인한다.
3. EUC-JP로 변환 불가능한 게임 코드 역테스트가 실패하는지 확인한다.
4. 길이 초과 역테스트가 계속 실패하는지 확인한다.
5. Python 구문 검사와 전체 ISO preflight를 수행한다.
6. 실제 ISO 생성은 사용자가 GUI에서 다시 빌드하도록 하며, PPSSPP 화면에서 `장비 전체 설정` 출력을 확인한다.

## 변경 예정 파일

- `/tools/scripts/ys6_system_message_workspace.py`
- `/tools/scripts/ys6_integrated_build.py`
- `/tools/ys6_dialogue_viewer.py`
- `/docs/result/051-ys6-system-message-euc-runtime-encoding-fix.md`

## ROM 처리

- 원본 ISO는 수정하지 않는다.
- 계획 구현 및 preflight 단계에서는 새 ISO를 만들지 않는다.
- 사용자가 기존 출력 ISO를 GUI로 다시 빌드할 때만 `/patched` 작업본을 갱신한다.
