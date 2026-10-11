# 117. Ys VI SPECIAL VERSION 시스템 메시지 이식 결과

상태: 완료

## 결론

- 일반판에서 승인된 시스템 메시지 중 SPECIAL VERSION의 원문 위치와 대응되는 138개 위치를 모두 한글로 적용했다.
- 기존 EUC-JP 저장 경로로 표현할 수 없는 한글 45자는 시스템 메시지 전용 레거시 글리프 별칭으로 처리했다.
- 공용 한글 매핑 revision 7의 문자, 게임 코드, 폰트 인덱스 및 순서는 변경하지 않았다.
- 익명 화자명은 사용자 요청에 따라 적용을 보류했다.
- SPECIAL VERSION 전용 일본어·영문 문구는 117번 승인 번역 이식 범위에 포함하지 않았으며 후속 계획으로 분리한다.

## 수행 내용

- SPECIAL 실행 파일의 시스템 메시지 후보 332개를 전용 작업공간으로 생성했다.
- 일반판 승인 번역과 원문·위치가 대응되는 138개를 확정했다.
- 1차로 기본 EUC-JP 변환이 가능한 38개를 적용했다.
- 사용자가 키 설정 화면에서 `공격`, `도구사용`, `마법사용`, `되돌리기`, `뒤로`의 정상 출력을 확인했다.
- `점`, `검`, `좌` 3자의 시스템 별칭 시험 ISO를 만들었고 사용자가 `점프`, `검 교체 (좌/우)`의 정상 출력을 확인했다.
- 전체 승인 번역에 필요한 시스템 별칭 45자를 확정하고 나머지 42자를 추가했다.
- SPECIAL 원문 조사 자료에 등장하는 일본어 문자는 별칭 후보에서 제외했다.
- 승인 대응 위치 138개의 인코딩, 길이, 형식 토큰, 원문 바이트 및 BOOT/EBOOT 동기화를 검증했다.
- GUI의 SPECIAL VERSION 사전 검증과 ISO 빌더가 시스템 메시지 138개와 별칭 45자를 동일하게 사용하도록 통합했다.

## 실기 확인

- 기본 EUC-JP 경로 38개: 정상
- 시스템 별칭 시험 `점프`, `검 교체 (좌)`, `검 교체 (우)`: 정상
- 전체 확장 ISO: 사용자가 정상 작동 확인
- 익명 화자명: 적용 보류

## 검증 결과

- Python 구문 검사: 통과
- SPECIAL 공용 빌더 사전 검증: 통과
- 시스템 메시지 후보: 332개
- 승인 번역 적용 위치: 138개
- 시스템 별칭: 45자
- 시스템 메시지 인코딩 차단: 0개
- 길이 초과: 0개
- 형식 토큰 충돌: 0개
- 원문 위치 충돌: 0개
- 기존 IDM 번역: 6,156개 재검증 통과
- IDM 리소스 및 런타임 복사본: 각각 177개 재검증 통과
- 인물·몬스터명 70개 및 아이템 72개 회귀 검증 통과
- 공용 한글 매핑: revision 7, 975자 유지

## 생성·변경 파일

- `tools/patchdata/ys6_special_version/system-messages.json`
- `tools/patchdata/ys6_special_version/system-glyph-aliases.json`
- `tools/patchdata/ys6_special_version/build-config.json`
- `tools/scripts/ys6_special_system_message.py`
- `tools/scripts/ys6_special_system_aliases.py`
- `tools/scripts/ys6_special_remaining_idm_preflight.py`
- `tools/scripts/ys6_special_patch_builder.py`
- `tools/patchdata/work/current/117-ys6-special-version-system-message-speaker-port/system-message-build-report.json`
- `tools/patchdata/work/current/117-ys6-special-version-system-message-speaker-port/system-alias-audit.json`

## 최종 테스트 ISO

- 경로: `patched/117-ys6-special-version-system-message-speaker-port/Ys VI Special Version - 117-full-system-message-port.iso`
- 크기: 716,201,984바이트
- SHA-256: `BE15D345764BFFB4E808027B13AD6B2091C345FEB2E6C93E3678CE8973266638`
- 원본 SPECIAL VERSION ISO는 변경하지 않았다.

## 정리 가능한 시험 ISO

- `Ys VI Special Version - 117-system-message-port.iso`: 38개 기본 경로 시험본
- `Ys VI Special Version - 117-system-alias-proof.iso`: `점`, `검`, `좌` 별칭 시험본
- 위 두 파일은 최종 확장본 확인 후 삭제 가능한 작업본이다.

## 후속 작업

- `Quick Save`, `Quick Save Data`, `Media Player` 등 순수 영문이라 기존 일본어 추출에서 빠진 SPECIAL 전용 시스템 문구를 조사한다.
- SPECIAL 전용 일본어 후보와 함께 실제 사용자 표시 문구와 내부 디버그 문자열을 구분한다.
- 익명 화자명은 실제 표시 장면과 저장 위치가 확보될 때까지 보류한다.
