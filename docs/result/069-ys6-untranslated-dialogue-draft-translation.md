# 069. Ys VI 미번역 dialogue 초벌 번역 결과

## 결과

- `dialogue` 역할이며 `untranslated`였던 412개를 검토했다.
- 의미 있는 대사 374개를 한국어로 번역하고 `draft`로 변경했다.
- 말줄임표·감탄부호만 있는 28개와 내부 로딩 표식 10개는 번역하지 않고
  `untranslated`로 유지했다.
- 기존 override 및 다른 사용자 번역은 변경하지 않았다.

## 번역 구성

- 신규 수동 번역: 150개 레코드, 일본어 원문 127종
- 동일 원문의 기존 단일 번역 전파: 215개
- 기존 번역 후보가 여러 개인 원문의 문맥 선택: 9개
- 합계: 374개

## 번역 정책

- 기존 프로젝트 용어와 인명 표기를 우선했다.
  - `ウル`: 울
  - `リモージュ`: 리모쥬
  - 검 이름: 리발트, 브릴란테, 에릭실
- `\n`, `\x1`, `\x3`, `\x4` 등 게임 제어 토큰을 보존했다.
- color와 scale 마크업을 보존했다.
- ruby 읽는 법은 067 정책에 따라 한글 번역에서 제거했다.
- 게임 문자 코덱이 지원하지 않는 장식용 `♪`, `《`, `》`는 의미를 유지하는
  `!`와 작은따옴표로 바꿨다.
- 모든 변경 레코드에 069 초벌 번역 출처를 notes로 기록했다.

## 검증

- 원문 SHA-256 fingerprint를 확인하는 `apply_drafts` 경로로 적용했다.
- 정확히 374개 레코드만 변경됨을 확인했다.
- 예상 밖 필드 변경: 0개
- 빈 draft 번역: 0개
- 한글 번역 내 일본어 잔존: 0개
- 원문과 동일한 번역: 0개
- 제어 토큰 불일치: 0개
- 보존 필수 마크업 불일치: 0개
- 전체 작업공간 검증: `valid: true`, 오류 0개

## 임시 승격 사전 검증

- 실제 작업공간의 374개는 `draft`이므로 정상 빌드에는 아직 포함되지 않는다.
- 압축과 할당 여유를 확인하기 위해 별도 임시 작업공간에서 069 draft만
  override로 승격해 통합 사전 검증했다.
- 결과:
  - `valid: true`
  - override: 5,166개
  - XSO 그룹: 527개
  - 아카이브: 74개
  - 독립 경로: 518개
  - 글리프: 977개
  - 할당 공간 초과: 0개
  - 옵션 메뉴 이미지: 9개
  - 추가 이미지: 39개, 런타임 복사본 41/41

## 생성 파일

- 초벌 번역 fingerprint 배치:
  `tools/patchdata/work/current/069-dialogue-drafts.json`
- 수동 번역 원문 매핑:
  `tools/patchdata/work/current/069-manual-translations.json`
- 다중 후보 선택 매핑:
  `tools/patchdata/work/current/069-ambiguous-translations.json`
- 대상 선정 보고서:
  `tools/patchdata/work/current/069-selection-report.json`
- 검수용 CSV:
  `tools/patchdata/work/current/069-dialogue-drafts-review.csv`
- 통합 사전 검증 요약:
  `tools/patchdata/work/current/069-preflight-summary.json`
- 최종 품질 보고서:
  `tools/patchdata/work/current/069-validation-report.json`

## 남은 항목

- `dialogue + untranslated`는 38개 남아 있다.
  - 말줄임표·감탄부호 전용: 28개
  - `--load st--`, `--load ed--` 내부 로딩 표식: 10개
- 374개는 모두 검수 전 `draft`이며 사용자가 확인 후 override로 승인해야 실제
  GUI 패치 빌드에 포함된다.
- 임시 preview 및 임시 override 작업공간은 검증 후 삭제했다.
- 원본 ISO는 수정하지 않았다.
