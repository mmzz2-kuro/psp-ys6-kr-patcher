# 114. Ys VI SPECIAL VERSION 중복 글리프 코드 호환성 수정 결과

상태: 완료 (대사 실기 확인은 후속 일괄 검수로 이관)

## 결론

- SPECIAL VERSION에서 `쩔`과 `코`가 함께 사용하던 `0x817E` 중복을 제거했다.
- 정상 출력되던 `코=0x817E`, 가시 폰트 인덱스 60은 유지했다.
- 도달할 수 없던 `쩔`은 사용자 정의 코드 `0xF2DB`, 확장 폰트 인덱스 2304로 재배정했다.
- 일반판 매핑은 이미 `쩔=0x9575`, `코=0x9441`로 분리돼 있어 변경하지 않았다.

## 원인

- 109번의 안전 슬롯 배정은 폰트 인덱스의 중복은 막았지만, 원본 폰트 테이블 안에 같은 게임 코드를 가진 레코드가 여러 개인 경우를 걸러내지 못했다.
- SPECIAL VERSION 검색 함수 `0x2D518`~`0x2D550`은 테이블 앞에서부터 30바이트씩 선형 검색하고 첫 코드 일치에서 반환한다.
- 따라서 `0x817E`는 앞쪽 인덱스 60의 `코`만 반환하고 인덱스 86의 `쩔`에는 도달하지 못했다.

## 수행 내용

- 배포 매핑을 revision 5에서 revision 6으로 갱신했다.
- 기존 중복 `쩔` 행을 제거하고 확장 테이블 끝에 신규 행을 추가했다.
- 문자 수는 964자로 유지하고 폰트 테이블은 2,304개에서 2,305개로 확장했다.
- SPECIAL 빌더가 revision 6 최종 매핑을 권위 있는 입력으로 사용하도록 변경했다.
- 문자, 게임 코드, 폰트 인덱스 중 어느 하나라도 중복되면 GUI 사전 검증 단계에서 빌드를 거부하도록 했다.
- 이전 revision의 중복을 허용하던 예외 처리를 제거했다.
- `쩔`과 `코`의 최종 ISO 인코딩 및 신규 글리프 레코드를 검사하는 전용 감사 도구를 추가했다.

## 세이브 호환성

- `쩔` 16회와 `코` 8회의 확인된 사용처는 모두 `s_scene.idm` 대사·행동 설명 문자열이다.
- 저장 지점명을 전달하는 `save.xso.z`, 인물·몬스터명 및 시스템 메시지에는 두 글자가 사용되지 않는다.
- 기존 세이브가 보관하는 위치명 코드에는 영향을 주지 않으며, 정상 동작하던 `코=0x817E`도 유지했다.

## 검증 결과

- Python 구문 검사: 통과
- GUI 공용 빌더 `inspect`: revision 6, 964자 인식
- 매핑 문자 중복: 0건
- 매핑 게임 코드 중복: 0건
- 매핑 폰트 인덱스 중복: 0건
- SPECIAL IDM 번역 재적용: 6,156개
- 수정 독립 IDM: 177개
- 런타임 아카이브 복사본: 177개
- IDM 할당 공간 초과: 0건
- `쩔` 포함 문자열: 16개, `F2DB` 16회 일치
- `코` 포함 문자열: 8개, `817E` 8회 일치
- 신규 `쩔` 글리프: 인덱스 2304, 코드 `F2DB`, 생성 비트맵 일치
- BOOT/EBOOT 재추출 비교: 통과
- 일반판 공용 빌더 사전 검증 회귀: 통과

## 생성·변경 파일

- `tools/patchdata/ys6_special_version/hangul-mapping.json`
- `tools/patchdata/ys6_special_version/build-config.json`
- `tools/scripts/ys6_special_remaining_idm_preflight.py`
- `tools/scripts/ys6_special_patch_builder.py`
- `tools/scripts/ys6_special_duplicate_glyph_audit.py`
- `tools/patchdata/work/current/114-ys6-duplicate-glyph-code-compatibility/preflight-report.json`
- `tools/patchdata/work/current/114-ys6-duplicate-glyph-code-compatibility/duplicate-glyph-audit.json`
- `tools/patchdata/work/current/114-ys6-duplicate-glyph-code-compatibility/corrected-glyph-atlas.png`

## 테스트 ISO

- 경로: `patched/114-ys6-duplicate-glyph-code-compatibility/Ys VI Special Version - 114-glyph-code-fix.iso`
- 크기: 716,199,936바이트
- SHA-256: `7FB36CA411FBC46BF96708A4A92BDC06177C0244B9CF57DD491D599A4DCB8A12`
- 원본 SPECIAL VERSION ISO는 변경하지 않았다.
- 테스트가 끝난 뒤 이 ISO는 삭제 가능한 작업본이다.

## 실기 확인 권장 위치

- 초반부터 확인 가능한 `어쩔 수 없...` 계열 대사에서 `쩔`이 `코`처럼 표시되지 않는지 확인한다.
- 토쿠사의 `내 코`, `나의 코` 계열 대사에서 기존 `코`가 정상 표시되는지 확인한다.

## 사용자 완료 판정

- 2026-08-27 사용자가 현재 단계에서는 114번을 완료 처리하기로 했다.
- `어쩔 수 없...`와 `내 코` 계열의 실제 출력 확인은 향후 대사 전체 일괄 검수에서 함께 진행한다.
- 후속 검수에서 문제가 발견되면 114번을 재개하거나 별도 교정 계획으로 처리한다.
