# 113. Ys VI SPECIAL VERSION GUI 패치 통합 결과

상태: 완료(2026-08-27 사용자 GUI 동작 확인)

## 수행 내용

- 일반판 `ULJM-05009`와 SPECIAL VERSION `ULJM-05155` 원본 ISO를 SHA-256으로 자동 식별하도록 공통 빌더를 확장했다.
- SPECIAL VERSION용 revision 5 매핑, 최종 번역, runtime map 및 안전 폰트 seed BOOT/EBOOT을 `tools/patchdata/ys6_special_version` 배포 경로에 고정했다.
- `ys6_special_patch_builder.py`를 추가해 공통 `inspect`, `preflight`, `build` 흐름으로 112번 패치를 실행하도록 했다.
- GUI에서 ISO 판본을 백그라운드로 감지하고 판본명과 프로필을 표시하도록 했다.
- SPECIAL VERSION 감지 시 일반판 전용 옵션 메뉴·추가 이미지·엔딩 영상·XMB·아날로그 스틱 옵션을 자동 해제하고 비활성화한다.
- SPECIAL VERSION 기본 출력명을 `Ys VI Special Version - Korean Patched.iso`로 설정한다.
- 현재 번역 편집 탭은 일반판용으로 유지하고 SPECIAL VERSION 빌드는 검증된 고정 IDM 번역 데이터를 사용한다.

## 원본 ISO 처리 수정

- 초기 검증 중 109번 중간 ISO가 아니라 실제 원본 SPECIAL VERSION ISO를 GUI 입력으로 받아야 함을 재확인했다.
- 지원 원본 SHA-256을 `C7BFF86BB7AA9DE025B4717BE34516A3E52D88EF8AD9AA3696F048D4ECCAE1A9`로 고정했다.
- 109번에서 검증된 안전 폰트 변경은 seed BOOT/EBOOT으로 배포하고, 모든 IDM은 원본 ISO에서 직접 최종 상태로 재구성한다.
- 따라서 사용자는 중간 패치 ISO 없이 원본 SPECIAL VERSION ISO만 선택하면 된다.

## SPECIAL VERSION 자동 검증

- 적용 번역: 6,156개
- standalone IDM: 177개
- 런타임 아카이브 복사본: 177개
- revision 5 매핑: 964자
- 폰트 테이블: 2,304개
- 할당량 초과: 0개
- `s_4010` 남은 여유: 28바이트
- 번역 바이트, standalone IDM, 런타임 복사본 및 BOOT/EBOOT 재추출 검증: 통과
- GUI/공통 빌더 생성 ISO SHA-256: `9ED7E6BC1DA8A1FACEC490D546EEE78D40442BF082F43863E77A625C6A1CB51D`

## 일반판 회귀 검증

- 원본 일반판 자동 감지: 통과
- 전체 사전 검증: 통과
- 대사 override 5,288개 및 기존 XSO·아카이브·standalone 처리: 통과
- 옵션 메뉴 이미지, 추가 이미지, 엔딩 영상, XMB 이미지 적용 전달: 통과
- 아날로그 스틱 적용 8개 명령어/32바이트 변경 검증: 통과
- 할당량 초과: 0개

## 잘못된 입력 검증

- 이미 패치된 112번 ISO를 원본으로 선택한 경우 지원하지 않는 SHA-256으로 빌드 전에 차단됨을 확인했다.
- 원본과 출력 경로가 같거나 기존 출력 덮어쓰기 승인이 없는 경우 기존 차단 동작을 유지한다.

## 생성·변경 파일

- SPECIAL VERSION 배포 데이터: `tools/patchdata/ys6_special_version`
- SPECIAL VERSION 전용 빌더: `tools/scripts/ys6_special_patch_builder.py`
- 사전 검증·ISO 생성 기반: `tools/scripts/ys6_special_remaining_idm_preflight.py`
- 공통 프로필 감지·라우팅: `tools/scripts/ys6_patch_builder.py`
- GUI: `tools/ys6_dialogue_viewer.py`
- 자동 검증 보고서: `tools/patchdata/work/current/113-ys6-special-version-gui-integration/regression-report.json`
- 시험 ISO: `patched/113-ys6-special-version-gui-integration/Ys VI Special Version - 113-gui-build.iso`

## 알려진 사항

- SPECIAL VERSION에서는 일반판 전용 이미지·영상·아날로그 옵션을 적용하지 않는다.
- revision 4에서 상속된 `0x817E`의 `쩔/코` 중복은 113번 범위에서 변경하지 않았다.
- 원본에서 직접 생성한 113번 ISO는 109번 중간 ISO를 기반으로 한 112번 ISO와 전체 SHA-256이 다르지만, 최종 IDM 및 BOOT/EBOOT 산출물은 동일하며 모든 재추출 검증을 통과했다.

## 사용자 확인 항목

1. GUI에서 원본 SPECIAL VERSION ISO를 선택했을 때 `SPECIAL VERSION (ULJM-05155)`가 표시되는지 확인한다.
2. 일반판 전용 체크박스와 이미지 관련 버튼이 비활성화되는지 확인한다.
3. `사전 검증`과 `패치 ISO 만들기`가 GUI에서 완료되는지 확인한다.
4. GUI 생성 ISO에서 초반 대사와 색상 행동 설명이 정상 표시되는지 확인한다.

## 사용자 확인 결과

- 2026-08-27 사용자가 GUI의 SPECIAL VERSION 감지와 패치 생성 동작을 확인했다.
- 이후 발견되는 SPECIAL VERSION GUI 회귀 문제는 113번을 재개하거나 별도 수정 계획으로 처리한다.
