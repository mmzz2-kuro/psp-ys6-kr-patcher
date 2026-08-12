# 021 Ys VI 다중 XSO·런타임 아카이브 통합 빌더 결과

## 결과

검수 완료 번역을 원본 XSO SHA-256별로 묶고, 020 대응표에서 실제 런타임 엔트리를 찾아 폰트·EBOOT·XSO·압축 파일·여러 아카이브·ISO를 한 번에 생성하는 통합 빌더를 구현했다. 여러 ISO 파일은 원본 ISO를 한 번만 복사한 임시 파일에 적용하고 전체 검증 후 최종 경로로 원자적으로 승격한다.

현재 전체 번역 작업공간에는 `reviewed` 레코드가 0개이므로, 계획 019에서 고정한 오프닝 번역 9개를 회귀 입력으로 사용했다. 통합 빌더가 생성한 EBOOT, XSO, `.xso.z`, `s_0551.bin`과 최종 ISO는 인게임 검증을 마친 019 산출물과 각각 SHA-256 및 전체 바이트가 완전히 일치했다.

## 구현 파일

- 통합 빌더: `/tools/scripts/ys6_integrated_build.py`
- 다중 ISO 패처: `/tools/scripts/ys6_iso_multi_patch.py`
- 통합 빌더 테스트: `/tools/scripts/tests/test_ys6_integrated_build.py`
- 다중 ISO 패처 테스트: `/tools/scripts/tests/test_ys6_iso_multi_patch.py`

## 통합 빌더 동작

### 입력과 선택

- 번역 작업공간 검증
- `status == "reviewed"` 레코드만 선택
- 검수 번역이 0개면 ISO를 만들지 않고 중단
- 원문 SHA-256, 토큰, 마크업, NUL 및 문자열 인덱스 검증
- 020 대응표와 원본 ISO SHA-256 검증
- 누적 수정 EBOOT가 아닌 복호화 원본 EBOOT 해시 검증

### 대응과 충돌

- standalone 경로 대신 원본 XSO payload SHA-256으로 그룹화
- `exact_one_to_one` 및 명확한 `standalone_duplicate`만 허용
- 런타임 대응이 없거나 모호하면 중단
- 동일 payload·동일 인덱스에 서로 다른 번역이 있으면 충돌로 중단
- 동일 payload의 여러 standalone 경로가 공유하는 영향 범위를 manifest에 기록

### 빌드

- 기존 문자 매핑을 보존하고 새 한글만 안전 슬롯에 추가
- 복호화 원본 EBOOT에서 전체 글리프를 매번 재생성
- 여러 XSO의 가변 길이 문자열 재조립
- zlib 레벨 9 압축, CRC32·크기·왕복 검증
- 엔트리별 기존 할당 공간 검사
- 같은 아카이브의 여러 XSO를 하나의 아카이브 작업본에 누적 적용
- 수정 대상 외 엔트리와 아카이브 크기 보존

### 원자적 ISO 생성

- EBOOT와 수정 아카이브들을 manifest 기반으로 일괄 교체
- 원본 내부 파일의 크기·SHA-256 사전 검증
- extent 중첩과 할당 초과 차단
- 각 교체 파일의 ISO 재추출 검증
- 허용 extent 밖 변경 검사
- 성공 전에는 `.partial` ISO만 사용
- 전체 성공 후 최종 경로로 원자적 교체
- 실패 시 `.partial` 파일 삭제

## 019 회귀 빌드

입력:

- 검수 번역: 9개
- 원본 XSO: 1개
- 런타임 아카이브: 1개
- 글리프 매핑: 58개

할당 판정:

| 항목 | 결과 |
|---|---:|
| 원본 XSO | 4,516바이트 |
| 수정 XSO | 4,495바이트 |
| 수정 `.xso.z` | 1,964바이트 |
| 엔트리 할당 | 2,048바이트 |
| 남은 공간 | 84바이트 |

산출물 비교:

| 산출물 | 021 SHA-256 | 019와 비교 |
|---|---|---|
| EBOOT | `E302ABAC588FFDC65C6A885D68B51E160ECC6F140F4CFA0D33DFF95FC2F34A87` | 동일 |
| XSO | `5799FD427D21DDB821F97E7A80B185BB2A45B36C7CDABE795C480A7E521EDBB4` | 동일 |
| `.xso.z` | `ED4CC217BF195D6CC14B45EA35E3B4D927DCE0E1781464C9FA03F25A24DE6456` | 동일 |
| `s_0551.bin` | `C7178340479A1791419F5F2B50B5F3993BADE77486628FB53F9C1100D469F922` | 동일 |
| 최종 ISO | `0F33526C62BD04DC56390D900CEAE9312AC4AFB4F4FFA29F9A78D81D9E127AD7` | 전체 바이트 동일 |

최종 ISO 크기는 866,254,848바이트다. 내부 EBOOT와 `s_0551.bin`의 extent LBA도 원본과 동일하며 허용 범위 밖 변경은 0건이다.

019 ISO는 PPSSPP 새 게임에서 오프닝 번역 9개, 줄바꿈, 문장부호, 말줄임표 간격과 후속 이벤트가 이미 검증됐다. 021 ISO가 그 파일과 전체 바이트 단위로 같으므로 019 회귀 동작도 동일하다.

## 자동 검증

- 전체 단위 테스트: 63건 통과
- Python 바이트코드 컴파일: 통과
- 검수 번역 0건 차단 테스트
- 정확한 런타임 대응 그룹화 테스트
- 공유 payload 번역 충돌 차단 테스트
- 다중 ISO extent 적용 테스트
- 겹치는 ISO extent 차단 테스트
- 최종 ISO 내부 EBOOT·아카이브 재추출 해시 일치
- 원본 대비 허용 범위 밖 변경 0건
- 원본 ISO 분석 전후 SHA-256 동일

원본 ISO SHA-256:

`0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

## 산출물

- 최종 ISO: `/patched/021-multi-archive-build/Ys VI - multi-archive-korean-build.iso`
- 작업 경로: `/.work/ys6-multi-archive-builder`
- 빌드 manifest: `/.work/ys6-multi-archive-builder/build-manifest.json`
- 사전 검사: `/.work/ys6-multi-archive-builder/preflight-report.json`
- 번역 보고서: `/.work/ys6-multi-archive-builder/translation-report.csv`
- XSO 보고서: `/.work/ys6-multi-archive-builder/xso-report.csv`
- 아카이브 보고서: `/.work/ys6-multi-archive-builder/archive-report.csv`
- 글리프 보고서와 atlas, 매핑, 수정 EBOOT·XSO·아카이브 작업본

주요 보고서 SHA-256:

| 파일 | SHA-256 |
|---|---|
| `build-manifest.json` | `89A8A75253DA5D944BA53AA311DACF943F9797C15D0953EFE4ACC87225872A3B` |
| `preflight-report.json` | `95D6E3157F0D95EBABD7D73A2ED16B6A5AA7AA0B9810F416E3541FBF8EBED6AB` |
| `translation-report.csv` | `E4413B96E9566CB8946FEAD1F340EE4460CED26F7ADBEDA284DFBA2359C381A5` |
| `xso-report.csv` | `B2B3D7AD0AAD1CC80D0D750AF0CE3FAB966FABC4B0B6E0BDCA189D1B7CD75288` |
| `archive-report.csv` | `1CA3ED048CBF081ABC316A1183DC85D0C89AD0D65E0A0E43E5AF8C33C42E9D51` |

CSV는 UTF-8 BOM으로 기록한다. 중간 ISO는 최종 검증 후 남기지 않았다.

## 보류된 검증

서로 다른 런타임 XSO 또는 아카이브에 속한 실제 `reviewed` 번역이 아직 없으므로 다음 항목은 데이터 준비 전 보류한다.

- 서로 다른 두 아카이브를 포함한 실제 ISO 빌드
- 각 아카이브 대사의 PPSSPP 인게임 출력
- 한 이벤트의 검증이 다른 아카이브의 검증을 대신하지 않는 독립 실행 확인
- `standalone_duplicate` 실제 번역의 게임 내 영향 범위 확인

통합 코드와 다중 extent 적용은 단위 테스트로 검증됐지만, 실제 다중 아카이브 인게임 검증을 완료한 것으로 과장하지 않는다.

## `s_0551` 확장 번역 인게임 검증

사용자가 전체 번역 작업공간에 추가한 번역 중 런타임 대응이 확정된 `s_0551`의 29개를 별도 검수 입력으로 준비해 021 ISO를 갱신했다.

- 적용 인덱스: 35~51, 53~64
- 인덱스 52: 번역문이 없어 일본어 원문 유지
- 인덱스 56: 사용자 승인에 따라 검수 복사본에서만 원문과 같은 줄바꿈 복원
- 적용 글리프: 119개
- 수정 XSO: 4,401바이트
- 수정 `.xso.z`: 1,897바이트
- 기존 할당 내 남은 공간: 151바이트
- 전체 테스트: 65건 통과
- 허용 범위 밖 ISO 변경: 0건

최종 산출물:

| 항목 | SHA-256 |
|---|---|
| EBOOT | `E6B779D399366C947BED750183D1F76586A8D671783E4155EFCC8A1AA34E9DED` |
| XSO | `B464966CB7EA0F1BAC0CD2B83C6C56147578B091176B9E5270188EC2512474A9` |
| `.xso.z` | `7981F0A46DAE39C90EA35545A8A388D0E903962D742B364272B6481806FA2F30` |
| `s_0551.bin` | `75970A0BD34D575EBE9CD6F57E4A295E4AC5165267CFB0DBD64BF7CFE356A829` |
| 최종 ISO | `B6B924719E65B40205196403133C2A4B8E967A4891D793409FCB4CCC537C2CF2` |

PPSSPP 새 게임에서 기존 번역과 신규 번역이 정상 출력되고 후속 이벤트도 정상 진행된 것을 사용자가 확인했다. 따라서 `s_0551` 단일 아카이브에 대한 29개 일괄 적용은 인게임 검증 완료로 판정한다.

## 알려진 제한

- 기존 엔트리 할당을 하나라도 초과하면 전체 빌드가 중단된다.
- 초과 항목을 제외하고 일부만 반영하는 모드는 제공하지 않는다.
- 아카이브 전체 재배치·확장은 아직 지원하지 않는다.
- XSO 외 메뉴·아이템·이미지·시스템 문자열은 처리하지 않는다.
- 현재는 비GUI 스크립트이며 사용자가 직접 쓰는 최종 패치 GUI와 연결되지 않았다.

## 다음 단계

다음 작업은 새 기술 구현보다 실제 번역 확대가 우선이다. 대사 GUI에서 서로 다른 런타임 아카이브에 대응되는 작은 이벤트 묶음 두 개 이상을 번역·검수한 뒤 021 빌더로 반영하고 인게임 확인한다.

그 과정에서 할당 초과가 실제로 발생하면 초과 XSO, 필요 증가량과 대상 아카이브를 근거로 `022 아카이브 전체 재배치` 계획을 작성한다. 초과 없이 통합 빌드가 검증되면 다음으로 사용자용 Python GUI 패치 도구와 연결한다.
