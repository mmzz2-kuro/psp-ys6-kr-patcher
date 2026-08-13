# 042. 안전 부분집합 테스트 ISO 빌드 결과

## 결과

전체 draft 4,628개 중 현재 빌더로 안전하게 처리할 수 있는 4,462개를 임시 override로 구성하여 테스트 ISO를 생성했다. 제외된 166개는 별도 Markdown 및 JSON 보고서에 기록했다.

## 테스트 ISO

- 경로: `/patched/042-safe-subset-test/Ys VI - 4462-dialogues-korean-test.iso`
- 크기: 866,254,848바이트
- SHA-256: `CA858ADA035813DFAA1AE7718E93AC73D0E6CE60225FEC6D6282A0C518703CE6`
- 원본 ISO SHA-256: `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

## 반영 범위

- 대사 override: 4,462개
- XSO payload: 446개
- 아카이브: 44개
- 독립 XSO: 417개
- 검토된 인물명: 14개
- 생성 글리프: 939개
- 공간 초과: 0개

## 제외 범위

- 전체 제외: 166개
- many-to-many 런타임 매핑: 28개
- 공유 payload 번역 충돌: 138개, 68그룹

검토 문서:

- `/docs/result/042-ys6-excluded-166-dialogues.md`
- `/.work/ys6-safe-subset-test/excluded-166.json`

## 검증

- 안전 부분집합 override 수: 4,462개 확인
- 제외 차집합: 166개 확인
- preflight: 통과
- 실제 빌드 manifest: `valid: true`
- XSO·아카이브 공간 초과: 없음
- 생성 ISO 존재 및 SHA-256 확인
- 원본 ISO와 출력 ISO 해시가 다름
- 원본 번역 작업공간 SHA-256 유지: `67D7193C34159BAD6E978C9A63AF0406328C2346CF8295FAF85C02411496BAB8`
- 원본 번역 작업공간은 draft 4,628개 상태를 유지함

## 생성·변경 파일

- `/patched/042-safe-subset-test/Ys VI - 4462-dialogues-korean-test.iso`
- `/tools/scripts/ys6_excluded_subset_report.py`
- `/.work/ys6-safe-subset-test/excluded-166.json`
- `/.work/ys6-safe-subset-test/preflight/`
- `/.work/ys6-safe-subset-test/build/`
- `/docs/result/042-ys6-excluded-166-dialogues.md`
- `/docs/result/042-ys6-safe-subset-iso-build.md`

## 알려진 제한

- 제외된 166개는 이 테스트 ISO에서 일본어 원문으로 남는다.
- 공유 payload 충돌과 many-to-many 런타임 매핑을 해결해야 4,628개 전체판을 만들 수 있다.
- 전체 게임 플레이 및 화면 폭 검증은 아직 수행하지 않았다.

## 정리 대상

- 이 ISO는 166개 제외 문제가 해결되기 전까지 사용하는 임시 테스트판이다.
- 완전판 생성 후 `/patched/042-safe-subset-test/Ys VI - 4462-dialogues-korean-test.iso`를 삭제 후보로 관리한다.
- `/.work/ys6-safe-subset-test`와 `/.work/ys6-all-drafts-test-build`도 완전판 완료 후 정리할 수 있다.

## ROM 처리

- 원본 ISO는 변경하지 않았다.
- 기존 패치 ISO는 덮어쓰지 않았다.
- 새 테스트 ISO 한 개만 생성했다.
