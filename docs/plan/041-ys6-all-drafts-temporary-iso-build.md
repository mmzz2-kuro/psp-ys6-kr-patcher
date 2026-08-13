# 041. 전체 draft 임시 override 테스트 ISO 빌드 계획

## 목적

현재 `draft` 대사 4,628개를 원본 작업공간에서 변경하지 않고 임시 복사본에서 `override`로 승격하여 통합 패치 ISO를 만든다. 실제 게임에서 전체 번역의 출력 상태를 확인하기 위한 테스트 빌드다.

## 핵심 방침

- `/tools/config/dialogue-translations.json`의 상태는 변경하지 않는다.
- `.work/ys6-all-drafts-test-build`에 임시 override 작업공간을 만든다.
- 원본 ISO는 읽기 전용 입력으로 사용하고 수정하지 않는다.
- 기존 `/patched` ISO를 덮어쓰지 않는다.
- 새 결과는 `/patched/041-all-drafts-test-build`에 한 개만 생성한다.
- 우선 preflight를 실행하며, 실패하면 ISO를 억지로 만들지 않고 원인을 기록한다.

## 입력

- 원본 ISO: `/roms/Ys VI - Napishtim no Hako (Japan).iso`
- 대사 작업공간: `/tools/config/dialogue-translations.json`
- 인물명 작업공간: `/tools/config/cast-names.json`
- 패치 데이터: `/tools/patchdata`
- 폰트: `C:/Windows/Fonts/gulim.ttc`

## 예상 출력

- 임시 승격본: `/.work/ys6-all-drafts-test-build/dialogue-translations.override.json`
- preflight 결과: `/.work/ys6-all-drafts-test-build/preflight`
- 테스트 ISO: `/patched/041-all-drafts-test-build/Ys VI - all-drafts-korean-test.iso`
- 결과 문서: `/docs/result/041-ys6-all-drafts-temporary-iso-build.md`

## 작업 절차

1. 현재 번역 작업공간의 SHA-256과 상태별 수량을 기록한다.
2. 전체 `draft`를 복사본에서만 `override`로 승격한다.
3. 임시 승격본에 대해 작업공간 검증을 실행한다.
4. 통합 빌더가 임시 작업공간을 입력으로 받을 수 있도록 비GUI 빌드 호출을 구성한다.
5. preflight를 먼저 실행한다.
6. 공유 payload 충돌, 런타임 매핑, 압축 여유, 글리프 수 및 인코딩 실패 여부를 확인한다.
7. preflight가 통과할 때만 테스트 ISO를 생성한다.
8. 생성 ISO의 존재, 크기, SHA-256과 빌드 manifest를 확인한다.
9. 원본 작업공간이 변경되지 않았는지 SHA-256으로 재확인한다.
10. 결과 문서를 작성한다.

## 예상 위험 및 처리

### 공유 payload 번역 충돌

계획 038에서 66개 공유 payload 충돌 그룹이 발견되었다. 전체 승격본은 이 문제로 preflight가 실패할 가능성이 있다.

- 같은 실제 XSO payload와 같은 문자열 인덱스에 서로 다른 번역이 지정되면 임의로 하나를 선택하지 않는다.
- 실패 시 충돌 목록을 작성하고 ISO 생성은 중단한다.
- 사용자가 별도로 번역을 통일한 후 다시 빌드한다.

### many-to-many 런타임 매핑

- `ridepedestal` 등 지원하지 않는 런타임 매핑이 포함되면 해당 대상을 조용히 제외하지 않는다.
- preflight 실패 대상으로 명시하고 후속 계획으로 분리한다.

### 출력 용량 및 글리프

- 모든 번역 문자를 인코딩하고 필요한 한글 글리프를 생성한다.
- XSO 재구축, 압축 및 아카이브 할당 공간 검사를 통과해야 한다.
- 공간 초과나 글리프 슬롯 부족이 발생하면 ISO를 만들지 않는다.

## 검증 기준

- 원본 번역 작업공간 상태가 `draft` 4,628개, `override` 0개로 유지된다.
- 임시 작업공간은 `override` 4,628개이며 검증 오류가 0개다.
- preflight가 통과해야만 ISO를 생성한다.
- 생성 시 원본 ISO와 출력 ISO의 경로 및 SHA-256이 달라야 한다.
- 생성 ISO는 `/patched/041-all-drafts-test-build`에만 둔다.
- 빌드 manifest, 번역·XSO·아카이브 보고서를 보존한다.

## 보류 사항

- 이번 테스트 ISO의 실제 게임 전 구간 플레이 검증
- 화면 폭이 긴 대사 교정
- 공유 payload와 many-to-many 문제가 발견될 경우의 임의 자동 해결
- 원본 작업공간의 draft를 실제 override로 일괄 전환

## 정리 방침

- 이 ISO는 임시 테스트 빌드임을 파일명과 결과 문서에 명시한다.
- 이슈 완료 후 삭제할 수 있도록 결과 문서에 경로와 용도를 기록한다.
- `.work`의 임시 승격본과 빌드 산출물도 정리 대상으로 기록한다.

## 상태

- 계획 확인 완료
- 임시 override 승격 및 검증 완료
- 전체 preflight는 런타임 매핑 문제로 중단
- 안전하게 빌드 가능한 부분집합 분석 완료
- ISO 미생성
- 결과 문서: `/docs/result/041-ys6-all-drafts-temporary-iso-build.md`
