# 044. 전체 4,628개 대사 테스트 ISO 빌드 계획

## 목적

제어문자, 루비, 특수문자, many-to-many 매핑 및 공유 payload 충돌 처리가 끝난 전체 draft 4,628개를 임시 override로 승격하여 완전판 테스트 ISO를 생성한다.

## 입력

- 원본 ISO: `/roms/Ys VI - Napishtim no Hako (Japan).iso`
- 원본 대사 작업공간: `/tools/config/dialogue-translations.json`
- 임시 override 작업공간: `/.work/ys6-many-to-many-043/recheck-all-4628.json`
- 인물명 작업공간: `/tools/config/cast-names.json`
- 패치 데이터: `/tools/patchdata`
- 폰트: `C:/Windows/Fonts/gulim.ttc`

## 보존 원칙

- 원본 ISO는 읽기 전용 입력으로 사용한다.
- 원본 대사 작업공간의 draft 4,628개 상태는 변경하지 않는다.
- 기존 `/patched/042-safe-subset-test` ISO를 덮어쓰거나 삭제하지 않는다.
- 새 ISO는 별도 044 폴더에 한 개만 생성한다.

## 출력

- ISO: `/patched/044-full-dialogue-test/Ys VI - full-4628-dialogues-korean-test.iso`
- 빌드 작업 폴더: `/.work/ys6-full-dialogue-test/build`
- 결과 문서: `/docs/result/044-ys6-full-4628-dialogue-test-iso-build.md`

## 사전 확인 결과

직전 전체 preflight 결과:

- override: 4,628개
- XSO payload: 460개
- 아카이브: 49개
- 독립 XSO: 448개
- 인물명: 14개
- 글리프: 945개
- 공간 초과: 0개
- 공유 payload 충돌: 0개
- 결과: 통과

## 작업 절차

1. 원본 ISO, 원본 작업공간 및 임시 override 작업공간 SHA-256을 기록한다.
2. 임시 override 작업공간이 정확히 4,628개이며 검증 오류가 없는지 재확인한다.
3. 기존 출력 파일이 없는지 확인한다.
4. 통합 빌더의 `build` 모드로 새 ISO를 생성한다.
5. build manifest의 `valid`, override, XSO, 아카이브, 독립 XSO, 글리프 및 overflow를 확인한다.
6. 출력 ISO의 크기와 SHA-256을 기록한다.
7. 출력 ISO가 원본 ISO와 다른 해시인지 확인한다.
8. 원본 ISO와 원본 작업공간의 SHA-256이 작업 전후 동일한지 확인한다.
9. 결과 문서를 작성한다.

## 검증 기준

- 전체 대사 override가 정확히 4,628개여야 한다.
- build manifest가 `valid: true`여야 한다.
- 공간 초과가 없어야 한다.
- many-to-many 대상의 모든 런타임 아카이브 및 독립 XSO가 빌드 보고서에 포함되어야 한다.
- 새 ISO가 지정된 `/patched/044-full-dialogue-test`에 존재해야 한다.
- 원본과 출력 ISO의 SHA-256이 달라야 한다.
- 원본 작업공간은 draft 4,628개, conflict 0개, override 0개를 유지해야 한다.

## 실패 처리

- 빌드 중 새로운 오류가 발생하면 항목을 임의 제외하지 않는다.
- 실패한 출력 ISO가 완전한 파일로 검증되지 않으면 결과물로 취급하지 않는다.
- 오류 원인과 남은 임시 파일을 결과 문서에 기록한다.

## 정리 대상

- 042의 4,462개 ISO는 044의 게임 검증이 끝난 뒤 삭제 후보가 된다.
- 044 ISO도 최종 배포판이 아니라 전체 번역 검증용 테스트판이다.
- `.work/ys6-full-dialogue-test`는 최종 패치 완료 후 정리할 수 있다.

## 상태

- 계획 확인 완료
- 전체 ISO 빌드 및 검증 완료
- 결과 문서: `/docs/result/044-ys6-full-4628-dialogue-test-iso-build.md`
