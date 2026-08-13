# 035. Ys VI Windows 한국어 대사 추출기 및 PSP draft 연계 결과

## 결과 요약

Windows판 Ys VI 한국어 패치에서 전체 XSO 대사를 Unicode 한글로 추출하고 PSP판 대사 작업공간에 안전하게 대응하는 파이프라인을 구현했다.

- NNI/NA 색인 항목: 1,343개
- 압축 데이터 검증: 1,343개 전부 통과
- XSO: 1,182개 전부 파싱 성공
- Windows 문자열: 7,096개
- 한글 변환 성공: 7,096개
- 미해결 문자열 및 문자 코드: 0개
- PSP 경로·인덱스 정확 대응: 6,559개
- 구조 검토 필요: 433개
- PSP 미대응: 104개
- 새 Windows 번역 `draft` 적용: 3,772개
- 기존 번역 `draft` 보존: 671개
- 기존 `override` 보존: 142개

사용자 확인을 받은 뒤 새 후보 3,772개를 `/tools/config/dialogue-translations.json`에 `draft`로 적용했다. `override`는 변경하지 않았으므로 현재 패치 빌드 결과에는 자동으로 들어가지 않는다.

## 구현 파일

### `/tools/scripts/ys6_windows_archive.py`

- `data_us.ni`의 `NNI\0` 헤더와 난독화 색인 해석
- `data_us.na` 항목 읽기
- `.z`의 zlib 해제, 원본 크기 및 CRC32 검증
- 목록, 선택 추출 및 전체 무추출 검증 명령
- 절대 경로·상위 경로·드라이브 경로 차단

### `/tools/scripts/ys6_windows_korean_codec.py`

- 외부 라이브러리 없이 TrueType sfnt, cmap, post, loca, glyf 테이블 해석
- CP949 코드 위치의 패치 글리프와 Unicode 한글 글리프 윤곽 비교
- 동일 `glyf` SHA-256을 이용한 전용 문자표 자동 복원
- 고유하게 수정된 28개 글리프는 격자 렌더와 PSP 문맥으로 별도 검증
- 전용 코드 디코딩 및 미해결 코드 보고

### `/tools/scripts/ys6_windows_dialogue_extract.py`

- 1,182개 XSO를 기존 `ys6_xso.py`로 파싱
- 전체 문자열을 Unicode 한국어로 변환
- 원시 바이트, SHA-256, 경로, 인덱스 및 변환 상태 기록

### `/tools/scripts/ys6_windows_dialogue_match.py`

- Windows 경로를 PSP ISO 경로로 정규화
- XSO별 문자열 수, 인덱스 및 주요 제어 토큰 비교
- `exact`, `review`, `unmatched` 분류
- 기존 `override`와 번역된 `draft` 보존
- 비대사 역할 및 한글이 없는 리소스 제외
- 미리보기와 명시적 `--apply-drafts` 출력 경로 분리

## 문자 코드 복원

Windows XSO의 바이트 `8A8891A6208D8D8F868CFA`를 일반 CP949로 읽으면 무의미한 음절이 나오지만, 패치 폰트 `im04.dt`로 렌더링하면 `남자 목소리`가 표시된다.

이는 패치가 CP949 코드 위치의 글리프 외형을 다른 한글로 치환했기 때문이다. 구현한 코덱은 같은 폰트 안에서 치환 글리프와 정상 Unicode 한글 글리프의 `glyf` 데이터를 비교하여 4,772개 코드를 자동 복원했다. 추가로 28개 고유 글리프를 확인하여 최종 4,800개 매핑을 만들었다.

- 문자표: `/tools/patchdata/windows-korean-code-map.json`
- 전체 Windows 대사: `/tools/patchdata/windows-korean-dialogues.json`
- 코드 충돌: 0개
- 전체 XSO에서 미해결 코드: 0개

## PSP 대응 및 적용 결과

| 분류 | 수량 | 처리 |
|---|---:|---|
| 정확 대응 | 6,559 | 역할 및 기존 상태에 따라 draft 후보 판정 |
| 구조 검토 | 433 | 자동 적용하지 않음 |
| PSP 미대응 | 104 | 자동 적용하지 않음 |
| 기존 draft | 671 | 보존 |
| 기존 override | 142 | 보존 |
| 비대사 역할 | 1,814 | 제외 |
| 한글 없는 리소스 | 160 | 제외 |
| 신규 draft | 3,772 | 사용자 확인 후 적용 |

적용 후 다시 대응 보고서를 생성했으며 남은 `draft_candidate`는 0개이다. 구조 검토 및 미대응을 합친 537개는 `review_only`로 남겼다.

## 검증

### 아카이브

- NNI 파일명 해시 검증 통과
- 1,343개 데이터의 zlib 해제, 원본 크기 및 CRC32 검증 통과
- `../`, 절대 경로 및 드라이브 경로 거부 시험 통과

### XSO 및 코덱

- 1,182개 XSO 파싱 오류 0건
- 7,096개 문자열 변환 오류 0건
- 미해결 코드 0개
- `adolsleep` 표본 35개 문자열의 한글 변환 및 PSP 인덱스 대응 확인

### 번역 작업공간

- 레코드 수: 7,424개
- `override`: 142개, 적용 전후 동일
- 신규 Windows draft: 3,772개
- `ys6_translation_workspace.py validate`: `valid=true`, 오류 0건
- 경고 4,486건은 번역이 입력된 `draft`를 알리는 기존 검증기의 의도된 경고이다.

### 원본 무변경

분석 및 적용 후에도 Windows 원본 해시가 계획 034의 값과 동일하다.

| 파일 | SHA-256 |
|---|---|
| `data_us.na` | `7C271678CCF4F4D40B554981D2F4FE8BC9AD5567202C9CE9F8B6ACE76FF27324` |
| `data_us.ni` | `6709A9C8642BFC9B5EE6D3ECDD84B14258CAF0362636D1F33406DC97A2C51D5B` |
| `im04.dt` | `5EF68C0D7412DD193C5DCBBBB1C712740BA4BE2F09919CA093762BA6E3E30CF6` |
| `im04.fot` | `F98341F49CF6DC1DE16A66C99DC93177C348D1E2B011188A44CE61BC8366B9FE` |

## 산출물

- `/tools/patchdata/windows-korean-code-map.json`
- `/tools/patchdata/windows-korean-dialogues.json`
- `.work/ys6-windows-korean-extraction/psp-match-report.pre-apply.json`
- `.work/ys6-windows-korean-extraction/psp-match-report.post-apply.json`
- `.work/ys6-windows-korean-extraction/dialogue-translations.preview.json`
- `.work/ys6-windows-korean-extraction/unresolved-glyph-atlas.png`
- `.work/ys6-windows-korean-extraction/report.json`

## 알려진 사항

- Windows판 번역은 기존 한국어 패치의 문장을 그대로 추출한 것이므로 문체, 띄어쓰기 및 오탈자는 사용자 검수가 필요하다.
- Windows판에서 루비 태그와 플레이어명 변수를 실제 한글로 풀어 쓴 경우가 있다.
- 구조가 다르거나 PSP에 없는 537개 문자열은 안전을 위해 자동 적용하지 않았다.
- 새 번역은 모두 `draft`이므로 사용자가 GUI에서 확인하고 `override`로 전환해야 실제 PSP 패치에 반영된다.
- 이번 작업에서는 PSP ISO를 빌드하거나 수정하지 않았다.

## 상태

- 구현 완료
- 전체 Windows 대사 추출 완료
- 사용자 확인 후 3,772개 draft 적용 완료
- 원본 무변경 확인 완료
