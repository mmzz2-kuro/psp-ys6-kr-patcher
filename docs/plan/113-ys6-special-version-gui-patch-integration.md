# 113. Ys VI SPECIAL VERSION GUI 패치 통합 계획

상태: 완료(2026-08-27 사용자 GUI 동작 확인)

## 배경

- 현재 GUI와 `ys6_patch_builder.py`는 일반판 `ULJM-05009` 원본 해시와 XSO 기반 패치 자산을 전제로 한다.
- SPECIAL VERSION `ULJM-05155`는 실행 파일, IDM 대사, 런타임 아카이브 및 폰트 구조가 일반판과 다르다.
- 112번에서 SPECIAL VERSION용 revision 5 매핑, 확장 BOOT/EBOOT, 6,156개 IDM 번역과 177개 런타임 복사본 적용 방식이 시험 ISO에서 검증됐다.
- 일반판용 옵션 메뉴·추가 이미지·엔딩 영상·XMB·아날로그 스틱 자산은 SPECIAL VERSION에 그대로 적용할 수 있다고 검증되지 않았다.

## 목적

- GUI가 선택된 ISO를 일반판과 SPECIAL VERSION으로 자동 식별하도록 한다.
- SPECIAL VERSION에서는 112번에서 검증한 전체 IDM 번역과 revision 5 폰트를 사전 검증 및 ISO 빌드에 동일하게 적용한다.
- 일반판 전용 부가 패치가 SPECIAL VERSION에 잘못 적용되지 않도록 프로필별 기능 상태를 명확히 표시한다.
- 사용자가 별도 명령행 작업 없이 `사전 검증`과 `패치 ISO 만들기` 버튼으로 SPECIAL VERSION 패치를 생성할 수 있게 한다.

## 1. 배포용 SPECIAL VERSION 패치 데이터 고정

- `tools/patchdata/ys6_special_version`에 GUI 빌드에 필요한 최소 산출물을 배치한다.
  - revision 5 `hangul-mapping.json`
  - 최종 IDM 번역 작업공간 또는 빌드용 정규화 레코드
  - 109번 runtime map
  - 재현성 검증용 입력 SHA-256과 기대 개수
- `work/current` 경로는 분석·개발 산출물로 유지하고 사용자 GUI가 직접 의존하지 않게 한다.
- 배포용 데이터에는 스키마 버전, 프로필 `ULJM-05155`, 매핑 revision 5와 6,156개 적용 위치를 기록한다.

## 2. ISO 프로필 자동 식별

- ISO SHA-256과 `PARAM.SFO`/실행 파일 정보를 이용해 다음 프로필을 구분한다.
  - 일반판 `ULJM-05009`
  - SPECIAL VERSION `ULJM-05155`
- 해시가 일치하지 않는 변형 ISO는 임의 처리하지 않고 지원하지 않는 원본으로 안내한다.
- GUI의 ISO 입력 영역에 감지된 판본과 프로필을 표시한다.
- 출력 기본 파일명도 감지된 판본에 맞춰 생성한다.

## 3. 빌더 프로필 라우팅

- `ys6_patch_builder.py`에 프로필 판별 및 빌드 라우팅 계층을 추가한다.
- 일반판은 기존 `ys6_integrated_build.py` 경로를 그대로 유지한다.
- SPECIAL VERSION은 112번 검증 로직을 재사용하는 전용 빌드 경로로 보낸다.
- 두 경로 모두 `inspect`, `preflight`, `build` 인터페이스와 결과 요약 형식을 통일한다.
- 원본 ISO를 직접 수정하지 않고 출력 ISO 또는 사전 검증 결과만 생성한다.

## 4. SPECIAL VERSION 사전 검증

- 다음 항목을 GUI 사전 검증 버튼에서 확인한다.
  - 원본 ISO와 배포용 패치 데이터 SHA-256
  - revision 4 선두 946개 매핑의 append-only 보존
  - revision 5 매핑 964자와 폰트 테이블 2,304개
  - 신규 코드·폰트 인덱스 충돌 여부
  - 6,156개 번역의 shared target conflict
  - standalone IDM과 런타임 아카이브 할당량
  - `s_4010` 최종 크기와 최소 여유
- 실패 시 GUI 로그에 대상 경로, 인덱스, 필요 크기와 할당 크기를 표시한다.

## 5. SPECIAL VERSION ISO 빌드

- standalone IDM 177개와 런타임 아카이브 복사본 177개를 함께 갱신한다.
- revision 5 확장 BOOT/EBOOT을 원본 ISO 끝의 신규 extent에 배치한다.
- directory record와 volume space size를 갱신한다.
- 생성 후 다음을 전수 재추출 검증한다.
  - 번역 바이트 6,156개
  - standalone IDM 177개
  - 런타임 복사본 177개
  - BOOT/EBOOT
- GUI에 결과 ISO 경로, SHA-256, 적용 개수와 최소 남은 용량을 표시한다.

## 6. 프로필별 GUI 옵션 처리

- 일반판 선택 시 기존 메뉴 이미지, 추가 이미지, 엔딩 영상, XMB 이미지 및 아날로그 스틱 체크박스 동작을 유지한다.
- SPECIAL VERSION 선택 시 검증되지 않은 일반판 전용 옵션은 자동 해제하고 비활성화한다.
- 비활성화된 항목에는 `SPECIAL VERSION 미지원` 사유를 상태 문구와 로그에 표시한다.
- SPECIAL VERSION 자체 지원 또는 별도 이식이 확인된 기능만 이후 독립 계획을 거쳐 활성화한다.
- 이미지 캐시 갱신과 일반판 글리프 매핑 갱신 버튼도 현재 프로필에 맞게 활성 상태를 제어한다.

## 7. GUI 작업 흐름

- ISO를 선택하면 백그라운드에서 프로필을 감지하고 상태를 갱신한다.
- SPECIAL VERSION의 기본 출력명은 `Ys VI Special Version - Korean Patched.iso`로 제안한다.
- `사전 검증`과 `패치 ISO 만들기`는 감지된 프로필을 같은 작업 스레드로 전달한다.
- 빌드 진행 중 기존 버튼과 체크박스 잠금, 진행 표시 및 오류 팝업 동작을 유지한다.
- 현재 번역 편집 탭은 일반판 작업공간 편집용으로 유지하며, SPECIAL VERSION 빌드는 검증된 고정 IDM 번역 데이터를 사용한다고 명시한다.

## 8. 회귀 및 자동 검증

- 일반판:
  - 기존 지원 ISO의 프로필 감지
  - 기존 사전 검증 요약과 옵션 전달
  - 옵션 체크 해제 시 사전 검증과 실제 적용이 함께 제외됨
- SPECIAL VERSION:
  - 프로필 감지와 옵션 비활성화
  - 사전 검증 6,156개 및 177개 복사본 보고
  - 시험 ISO SHA-256 재현 또는 모든 재추출 결과 일치
- 잘못된 ISO:
  - 두 프로필 어디에도 해당하지 않으면 빌드 시작 전 차단
- 기존 GUI 편집 저장, 필터 및 이미지 캐시 기능이 변경되지 않았는지 회귀 검사한다.

## 9. 사용자 실기 확인

- GUI에서 SPECIAL VERSION 원본 ISO를 선택했을 때 판본이 올바르게 표시되는지 확인한다.
- 비지원 옵션이 자동 해제·비활성화되는지 확인한다.
- GUI 사전 검증과 패치 ISO 생성이 모두 완료되는지 확인한다.
- 생성 ISO에서 초반 대사, 색상 행동 설명, 기존 시스템 메시지와 저장·불러오기를 확인한다.

## 산출물

- SPECIAL VERSION 배포용 패치 데이터: `tools/patchdata/ys6_special_version`
- 프로필 감지 및 빌드 라우팅: `tools/scripts/ys6_patch_builder.py` 및 전용 빌드 모듈
- GUI 변경: `tools/ys6_dialogue_viewer.py`
- 회귀 테스트 또는 검증 보고서: `tools/patchdata/work/current/113-ys6-special-version-gui-integration`
- 결과 문서: `docs/result/113-ys6-special-version-gui-patch-integration.md`

## 제외 범위

- SPECIAL VERSION용 옵션 메뉴·추가 이미지·엔딩 영상·XMB 이미지 신규 이식
- SPECIAL VERSION 아날로그 스틱 동작 변경
- SPECIAL VERSION IDM 번역을 GUI 편집 탭에서 직접 수정하는 별도 편집기
- revision 4에서 상속된 `0x817E` 중복 매핑 수정
- 해시가 다른 SPECIAL VERSION 변형 ISO의 자동 이식

## 위험 및 중단 조건

- 일반판 빌드 경로의 출력 또는 옵션 동작이 변경되면 통합을 완료하지 않는다.
- SPECIAL VERSION 원본 해시나 배포 데이터 해시가 다르면 빌드를 차단한다.
- 매핑 선두 946개 중 하나라도 변경되면 ISO를 생성하지 않는다.
- IDM 또는 아카이브 할당량 초과, shared target conflict가 발생하면 ISO를 생성하지 않는다.
- 비지원 일반판 자산을 SPECIAL VERSION에 자동 적용하지 않는다.

## 완료 기준

- GUI가 일반판과 SPECIAL VERSION을 자동 식별한다.
- SPECIAL VERSION 사전 검증과 패치 ISO 생성이 GUI 원버튼 흐름으로 동작한다.
- revision 5 폰트와 6,156개 IDM 번역이 standalone 및 런타임 복사본에 모두 적용된다.
- 일반판 전용 옵션이 SPECIAL VERSION에서 안전하게 차단된다.
- 일반판 기존 빌드와 GUI 기능의 회귀 검증을 통과한다.
- 사용자가 GUI 생성 SPECIAL VERSION ISO에서 한글 출력을 확인한다.
