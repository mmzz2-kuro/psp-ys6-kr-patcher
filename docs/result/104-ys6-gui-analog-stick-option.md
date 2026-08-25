# 104. Ys VI GUI 아날로그 스틱 패치 옵션 반영 결과

상태: 완료

## 수행 내용

- GUI 패치 빌드 영역에 `아날로그 스틱 적용` 체크박스를 추가했다.
- 102번 실기 검증 결과에 따라 체크박스 기본값을 선택 상태로 설정했다.
- 체크 상태를 데이터 새로고침, 사전 검증과 ISO 빌드 작업 스레드에 동일하게 전달하도록 연결했다.
- GUI 상태 요약에 `아날로그 스틱 적용` 또는 `아날로그 스틱 제외`가 표시된다.
- 사전 검증 및 빌드 중에는 다른 패치 옵션과 함께 체크박스가 비활성화된다.
- 명령줄의 기존 `--analog-stick` 옵션과 같은 빌더 경로를 사용한다.

## 빌더 보고 보완

- `preflight-report.json`과 빌드 summary에 다음 값을 기록한다.
  - `analog_stick_patch_enabled`
  - `analog_stick_instruction_change_count`
  - `analog_stick_changed_byte_count`
- `build-manifest.json` 입력 항목에 `analog_stick_patch_enabled`를 기록한다.
- manifest의 EBOOT 항목에 아날로그 패치 상세 보고서를 포함한다.
- 옵션 해제 시 이전 실행의 `analog-stick-report.json`을 제거해 현재 빌드 결과로 오인하지 않게 했다.

## 변경 파일

- `tools/ys6_dialogue_viewer.py`
- `tools/scripts/ys6_integrated_build.py`
- 102번에서 추가된 다음 파일과 빌더 연결을 재사용했다.
  - `tools/scripts/ys6_patch_builder.py`
  - `tools/scripts/ys6_analog_mode_patch.py`

## 검증 결과

- Python 문법 검사: 통과
- GUI 기본 체크 상태: 선택
- 입력 검사:
  - 선택 상태 `analog_stick_patch_enabled=true`
  - 해제 상태 `analog_stick_patch_enabled=false`
- 선택 상태 전체 사전 검증: 통과
  - 8개 명령 모두 `0x24040001`
  - 명령 변경 8개
  - 변경 바이트 32바이트
  - preflight, summary와 manifest 모두 `true`
  - manifest EBOOT 아날로그 상세 보고서 존재
- 해제 상태 전체 사전 검증: 통과
  - 8개 명령 모두 기존 `0x00002021`
  - 명령 변경 0개
  - 변경 바이트 0바이트
  - preflight, summary와 manifest 모두 `false`
  - manifest EBOOT 아날로그 상세 보고서 없음
  - 이전 `analog-stick-report.json` 제거 확인
- 두 검증 모두 기존 번역 5,284건, 이미지, 엔딩 영상과 XMB 입력을 포함했으며 할당 공간 초과는 없었다.

## 검증 자료

- 선택 상태: `tools/patchdata/work/current/104-gui-analog-stick-option/enabled`
- 해제 상태: `tools/patchdata/work/current/104-gui-analog-stick-option/disabled`

## 알려진 사항

- 102번과 동일하게 8개 입력 모드 명령만 변경하며 별도 데드존 보정은 적용하지 않는다.
- 이 옵션은 현재 GUI가 지원하는 ULJM-05009 전용이다.
- 103번 SPECIAL VERSION 테스트 ISO에는 적용되지 않는다.
- 이번 검증은 EBOOT와 전체 사전 검증으로 선택 상태를 확인했으므로 별도의 104번 테스트 ISO는 만들지 않았다.

## 정리 대상

- 원본 ISO는 변경하지 않았다.
- 새 임시 ROM을 생성하지 않았으므로 삭제 대상 ROM은 없다.
