# 034. Ys VI Windows 한국어 패치 대사 추출 분석 결과

## 결론

`/windowVersion`의 Windows판 한국어 패치에서 대사를 추출할 수 있다.

- `data_us.ni`에는 1,343개 항목이 있으며, 이 중 1,182개가 `.xso` 대사·이벤트 파일이다.
- 파일 경로가 PSP판과 직접 대응한다. 예: `map/s_02/s_020a/adolsleep.xso.z`.
- 압축을 해제한 Windows XSO는 PSP 분석 도구가 그대로 인식하는 `XSR\0` 구조이다.
- 표본 `adolsleep`은 Windows판과 PSP판 모두 문자열 35개이며, 문자열 인덱스와 내용 순서도 대응한다.
- 따라서 Windows판 번역을 PSP판 초벌 번역의 기준 데이터로 활용할 가능성이 높다.

단, XSO의 한글 바이트는 UTF-8·UTF-16·CP949·CP932 평문이 아니다. 한국어 패치 전용 문자 매핑을 사용하므로, 일반 문자 인코딩으로 읽으면 한자와 일본어처럼 보인다. 전체 자동 추출 전에 이 문자 매핑을 복원해야 한다.

## 조사 대상

| 파일 | 크기 | SHA-256 |
|---|---:|---|
| `windowVersion/release/data_us.na` | 16,361,403 | `7C271678CCF4F4D40B554981D2F4FE8BC9AD5567202C9CE9F8B6ACE76FF27324` |
| `windowVersion/release/data_us.ni` | 62,046 | `6709A9C8642BFC9B5EE6D3ECDD84B14258CAF0362636D1F33406DC97A2C51D5B` |
| `windowVersion/release/im04.dt` | 3,471,896 | `5EF68C0D7412DD193C5DCBBBB1C712740BA4BE2F09919CA093762BA6E3E30CF6` |
| `windowVersion/release/im04.fot` | 1,409 | `F98341F49CF6DC1DE16A66C99DC93177C348D1E2B011188A44CE61BC8366B9FE` |

분석 후에도 네 파일의 SHA-256이 동일하여 원본이 수정되지 않았음을 확인했다.

## 아카이브 분석

`data_us.ni`의 헤더와 난독화된 색인을 해석했다.

- 식별자: `NNI\0`
- 항목 수: 1,343
- 파일명 영역 크기: 40,542바이트
- 확장자 분포:
  - `.xso`: 1,182
  - `.dds`: 155
  - `.dat`: 5
  - `.sl`: 1
- `.z` 항목은 CRC32와 원본 크기 헤더 뒤에 zlib 데이터가 놓인다.

## XSO 표본 검증

다음 파일을 작업 영역에만 추출했다.

- 원본 항목: `map/s_02/s_020a/adolsleep.xso.z`
- 산출물: `.work/ys6-windows-korean-analysis/map/s_02/s_020a/adolsleep.xso`
- 압축 크기: 1,497바이트
- 해제 크기: 2,868바이트
- CRC32: `0x3B51047B`, 일치
- XSO SHA-256: `BD08AA744C81381D6F9ECB90FDF01C6AAB56B2FD72DA3B5615B0CE75DEA862EE`
- XSO 구조: `XSR\0`, 코드 워드 335개, 문자열 35개
- 기존 `tools/scripts/ys6_xso.py` 파싱: 정상

PSP판 동일 리소스 `PSP_GAME/USRDIR/data/map/s_02/s_020a/adolsleep.xso.z`도 문자열 35개이다. 인덱스 0은 PSP 원문 `男の声`에 대응하며 Windows 바이트는 `8A8891A6208D8D8F868CFA`이다. 문맥과 글자 수상 Windows 번역은 `남자 목소리`로 판단되지만, 이 바이트를 CP949나 CP932로 해석하면 해당 한글이 나오지 않는다.

## 폰트 및 문자 코드

`im04.dt`는 다음 특성을 가진 TrueType 폰트이다.

- 내부 이름: `Felghana`
- 글리프 수: 19,790
- Unicode Hangul 음절 `U+AC00`~`U+D7A3`의 글리프 이름 포함
- 일본어·한자 글리프도 함께 포함

일반 Unicode cmap으로 전용 코드 문자열을 렌더링하면 한글이 아니라 한자·일본어로 표시되었다. 확인 이미지는 `.work/ys6-windows-korean-analysis/adolsleep-render.png`에 두었다. 이는 XSO 원문 바이트와 실제 한글 사이에 별도 변환표 또는 게임의 코드페이지/글리프 선택 규칙이 있음을 뜻한다.

## PSP판 재사용 판단

구조적 대응 가능성은 높다.

1. Windows와 PSP의 XSO 경로가 동일하다.
2. XSO 컨테이너 구조를 기존 PSP 파서가 읽을 수 있다.
3. 표본의 문자열 개수와 인덱스 순서가 정확히 일치한다.
4. 제어 태그도 XSO 문자열 안에 유지된다.

따라서 문자 매핑만 복원하면 Windows 번역을 경로와 문자열 인덱스로 PSP 원문에 연결할 수 있다. 그래도 플랫폼별 문구 차이, 누락·추가 문자열, 줄 길이 차이가 있을 수 있으므로 자동으로 `override` 처리하면 안 된다. Windows 번역은 `draft` 후보로 가져오고 사용자가 검토한 항목만 기존 절차대로 `override`로 전환하는 것이 안전하다.

## 후속 구현 제안

다음 작업은 별도 계획으로 진행한다.

1. `/tools/scripts`에 NNI/NA 읽기 전용 추출기를 작성한다.
2. `im04.dt`와 XSO 표본을 이용해 전용 코드→Unicode 한글 변환표를 복원한다.
3. 여러 XSO에서 변환 결과와 PSP 원문 인덱스 대응을 교차 검증한다.
4. Windows 번역을 별도 JSON으로 추출한다.
5. 경로·인덱스·원문 구조가 일치하는 항목만 PSP 작업공간의 `draft` 후보로 병합한다.

## 생성 파일 및 변경 범위

- 계획 갱신: `/docs/plan/034-ys6-windows-korean-dialogue-extraction-analysis.md`
- 결과 문서: `/docs/result/034-ys6-windows-korean-dialogue-extraction-analysis.md`
- 임시 분석 파일:
  - `.work/ys6-windows-korean-analysis/map/s_02/s_020a/adolsleep.xso`
  - `.work/ys6-windows-korean-analysis/adolsleep-render.png`

`/windowVersion` 원본과 PSP 번역 작업공간에는 이번 분석으로 인한 변경을 적용하지 않았다. 기존 작업 트리에 있던 번역·스크립트 변경은 그대로 보존했다.

## 참고 자료

- Luigi Auriemma의 `xsoext`: Falcom Ys XSO가 게임 대사를 담으며 추출·재구축할 수 있음을 설명한다.
- 공개 NNI/NA 분석 구현의 헤더·색인 난독화·zlib 처리 방식을 표본에 대조했다.

## 상태

- 분석 완료
- 원본 무변경 검증 완료
- Windows 한국어 대사 추출 가능 판정
- 전용 문자 매핑 복원은 후속 작업
