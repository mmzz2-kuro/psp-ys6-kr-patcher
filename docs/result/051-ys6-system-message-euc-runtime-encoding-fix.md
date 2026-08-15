# 051. Ys VI 시스템 메시지 EUC-JP 런타임 인코딩 수정 결과

## 결과

시스템 메시지가 깨진 원인은 CP932 게임 글리프 코드를 EUC-JP 저장 영역에 직접 기록한 이중 변환 문제였다. 시스템 메시지 전용 인코더를 추가하여 EBOOT에는 EUC-JP 역변환 바이트를 기록하도록 수정했다.

## 수정 내용

### 시스템 메시지 전용 인코더

`/tools/scripts/ys6_system_message_workspace.py`에 `encode_system_translation`을 추가했다.

- 한글에 할당된 CP932 게임 코드를 원래 일본어 문자로 해석
- 원래 일본어 문자를 EUC-JP로 변환하여 EBOOT에 기록
- 일반 공백을 EUC-JP 전각 공백 `A1A1`로 기록
- 문장부호 정규화 후 EUC-JP 저장
- EUC-JP로 역변환할 수 없는 게임 코드는 오류로 차단

GUI 길이 계산도 공백을 2바이트로 계산하도록 수정했다. 통합 빌드는 일반 대사 인코더 대신 시스템 메시지 전용 인코더를 호출한다.

## 기준 문구 검증

번역:

```text
장비 전체 설정
```

EBOOT 저장 바이트:

```text
CEF4 CDCA A1A1 CEE7 CEC0 A1A1 CEF2 CECD 00
```

EUC-JP를 런타임과 같은 방식으로 CP932로 변환한 결과:

```text
97F2 9769 8140 97E5 97BE 8140 97F0 97CB
```

이는 현재 `mapping.json`의 `장`, `비`, `전`, `체`, `설`, `정` 코드 및 게임 전각 공백 `8140`과 일치한다.

preflight가 생성한 EBOOT `0x12CF34`에서도 다음 바이트를 확인했다.

```text
CEF4CDCAA1A1CEE7CEC0A1A1CEF2CECD0000000000000000000000
```

## 길이 충돌 처리

`SYS_00120DB4`는 기존 계산에서 공백을 1바이트로 보았기 때문에 override가 가능했지만, 실제 EUC-JP 전각 공백 기준으로는 `53/51`바이트다.

- 번역: `변경하려는 조작을 선택하고 아무 버튼을 누르세요`
- 번역 내용은 보존
- 상태를 `override`에서 `conflict`로 변경
- 메모에 `53/51바이트` 원인 기록

이 항목은 GUI에서 더 짧게 교정한 뒤 다시 override로 변경할 수 있다. 예시 축약안은 `변경할 조작을 고르고 버튼을 누르세요`다.

## 검증 결과

- 정방향 EUC-JP 인코딩: 통과
- EUC-JP → CP932 역변환 코드 대조: 통과
- 변환 불가능한 CP932 확장 코드 `0xFA40` 역테스트: 오류 발생 확인
- Python 구문 검사: 통과
- `git diff --check`: 오류 없음
- 전체 ISO preflight: 통과

```text
valid: true
dialogue override: 4665
xso: 463
archives: 49
standalone: 450
cast names: 58
items: 72
system messages: 47
glyphs: 971
overflow: 0
```

## 변경 파일

- `/tools/scripts/ys6_system_message_workspace.py`
- `/tools/scripts/ys6_integrated_build.py`
- `/tools/config/system-messages.json`
- `/docs/plan/051-ys6-system-message-euc-runtime-encoding-fix.md`
- `/docs/result/051-ys6-system-message-euc-runtime-encoding-fix.md`

## ROM 처리

- 원본 ISO는 수정하지 않았다.
- 새 ISO는 생성하지 않았다.
- `/tools/patchdata/work/current`의 preflight EBOOT와 보고서만 갱신했다.
