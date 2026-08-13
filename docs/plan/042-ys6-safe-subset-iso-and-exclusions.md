# 042. 안전 부분집합 테스트 ISO 및 제외 166개 문서화 계획

## 목적

계획 041에서 확인한 전체 draft 4,628개 중 현재 빌더로 안전하게 처리 가능한 4,462개만 임시 override로 구성하여 테스트 ISO를 생성한다. 제외되는 166개는 번역을 삭제하거나 변경하지 않고 원인별 전체 목록을 별도 문서와 기계 판독 가능한 보고서로 남긴다.

## 사용자 승인 범위

- 166개를 테스트 ISO에서 임시 제외한다.
- 4,462개 안전 부분집합으로 ISO를 생성한다.
- 제외 166개를 별도 문서로 기록한다.

## 입력과 보존 원칙

- 원본 ISO: `/roms/Ys VI - Napishtim no Hako (Japan).iso`
- 원본 번역 작업공간: `/tools/config/dialogue-translations.json`
- 안전 부분집합: `/.work/ys6-all-drafts-test-build/buildable.json`
- 원본 번역의 `draft` 상태와 번역문은 변경하지 않는다.
- 기존 `/patched` ISO를 덮어쓰지 않는다.

## 제외 구성

- many-to-many 런타임 매핑: 28개
- 공유 payload 번역 충돌: 138개
- 합계: 166개

제외 보고서에는 각 레코드의 다음 정보를 기록한다.

- 제외 원인
- ISO 경로, 맵, XSO 이름 및 문자열 인덱스
- 원문과 현재 번역
- XSO SHA-256
- 같은 payload를 공유하는 관련 경로와 번역 후보
- 후속 해결 방향

## 작업 절차

1. 원본 작업공간과 안전 부분집합의 SHA-256 및 상태 수를 재확인한다.
2. 전체 임시 override 4,628개와 안전 부분집합 4,462개의 키 차집합을 계산한다.
3. 차집합이 정확히 166개인지 확인한다.
4. 제외 레코드를 many-to-many 28개와 공유 payload 충돌 138개로 분류한다.
5. JSON 보고서와 Markdown 검토 문서를 생성한다.
6. 안전 부분집합으로 통합 preflight를 실행한다.
7. 글리프, 인코딩, XSO 재구축, 압축 여유 및 아카이브 배치 검증을 통과하면 ISO를 생성한다.
8. 생성 ISO의 크기와 SHA-256, build manifest 및 보고서를 확인한다.
9. 원본 작업공간과 원본 ISO가 변경되지 않았는지 재확인한다.
10. 결과 문서를 작성한다.

## 출력

- 테스트 ISO: `/patched/042-safe-subset-test/Ys VI - 4462-dialogues-korean-test.iso`
- 제외 JSON: `/.work/ys6-safe-subset-test/excluded-166.json`
- 제외 문서: `/docs/result/042-ys6-excluded-166-dialogues.md`
- 빌드 결과: `/docs/result/042-ys6-safe-subset-iso-build.md`
- 빌드 작업 폴더: `/.work/ys6-safe-subset-test/build`

## 검증 기준

- 전체 임시 override 4,628개에서 정확히 166개가 제외되어야 한다.
- 안전 부분집합 override는 정확히 4,462개여야 한다.
- preflight와 실제 빌드가 모두 성공해야 한다.
- 생성 ISO는 원본 ISO와 다른 SHA-256이어야 한다.
- 원본 작업공간 SHA-256은 작업 전후 동일해야 한다.
- 원본 번역 레코드의 상태는 변경하지 않는다.
- ISO 내부 검증 및 빌드 manifest가 `valid: true`여야 한다.

## 실패 처리

- 4,462개 부분집합에서도 새로운 충돌, 인코딩 실패, 글리프 부족 또는 압축 공간 초과가 나오면 임의로 추가 제외하지 않는다.
- 실패 지점과 추가 대상을 보고하고 ISO 생성을 중단한다.
- 기존 파일을 덮어쓰거나 원본을 수정하지 않는다.

## 정리 대상

- 생성 ISO는 166개 문제 해결 전까지의 임시 테스트판이다.
- 완전판이 생성되면 `/patched/042-safe-subset-test` ISO를 삭제 후보로 결과 문서에 기록한다.
- `.work/ys6-safe-subset-test`도 후속 작업 완료 후 정리할 수 있다.

## 상태

- 계획 확인 완료
- 제외 166개 보고서 생성 완료
- 안전 부분집합 preflight 및 ISO 빌드 완료
- 결과 문서: `/docs/result/042-ys6-safe-subset-iso-build.md`
