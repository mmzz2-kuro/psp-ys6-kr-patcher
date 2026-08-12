# 020 Ys VI 전체 런타임 아카이브 및 XSO 대응 분석 결과

## 결과

원본 ISO의 `PSP_GAME/USRDIR/data/arc` 아래 아카이브 222개를 읽기 전용으로 전수 분석했다. 모든 아카이브가 기존 `ys6_arc.py` 포맷으로 정상 파싱됐으며, 내부 `.xso.z` 344개도 압축 컨테이너와 XSO 구조 검증을 모두 통과했다.

계획 010의 standalone XSO 1,194개와 런타임 XSO를 비압축 payload SHA-256으로 비교한 결과, 런타임 XSO 344개 전부에 대응되는 standalone 원문을 찾았다. 340개는 일대일 대응이고 4개는 동일 payload를 여러 standalone 경로가 공유한다. standalone XSO 839개는 `/data/arc`에서 동일 payload를 찾지 못했으며, 다른 런타임 경로 또는 미사용·개발 잔존 데이터일 가능성이 있으므로 자동 추정하지 않고 `standalone_only`로 보존했다.

## 구현 파일

- 분석 스크립트: `/tools/scripts/ys6_runtime_archive_map.py`
- 단위 테스트: `/tools/scripts/tests/test_ys6_runtime_archive_map.py`

스크립트는 다음 작업을 수행한다.

- 원본 ISO SHA-256 사전 검증
- `/data/arc` ISO 9660 엔트리 전수 열거
- 아카이브 파일 테이블·엔트리 범위·할당 크기 검사
- `.xso.z` CRC32·비압축 크기·zlib EOF 검사
- 비압축 XSO 구조·문자열 수·SHA-256 검사
- standalone/런타임 payload 해시 대응 및 중복 분류
- JSON 정본, UTF-8 BOM CSV 3종 및 Markdown 요약 생성
- 합계·참조 키·`s_0551` 회귀 검증

## 분석 통계

| 항목 | 결과 |
|---|---:|
| 전체 아카이브 | 222 |
| 정상 아카이브 | 222 |
| 아카이브 레코드 | 8,918 |
| 내부 파일 엔트리 | 5,643 |
| standalone XSO | 1,194 |
| 런타임 `.xso.z` | 344 |
| 정상 런타임 XSO | 344 |
| 손상·미지원 런타임 XSO | 0 |
| 해시 대응 그룹 | 1,106 |
| 오류 | 0 |

### standalone XSO 기준

| 상태 | XSO 수 |
|---|---:|
| 일대일 대응 | 340 |
| 동일 payload 중복 | 15 |
| 런타임 미대응 | 839 |
| 합계 | 1,194 |

### 런타임 XSO 기준

| 상태 | XSO 수 |
|---|---:|
| 일대일 대응 | 340 |
| 여러 standalone이 공유 | 4 |
| 런타임 단독 | 0 |
| 손상·미지원 | 0 |
| 합계 | 344 |

런타임 XSO가 여러 아카이브에 중복된 `runtime_duplicate` 또는 `many_to_many` 사례는 발견되지 않았다.

## 중복 대응 4그룹

1. `Buruburu.xso.z`: standalone 3개 → `s_6600.bin`의 런타임 엔트리 1개
2. `s_2005.xso.z`: standalone 2개 → `s_2005.bin`의 런타임 엔트리 1개
3. `StartRelease.xso.z`: standalone 3개 → `s_4610.bin`의 런타임 엔트리 1개
4. `near_oruha_tera.xso.z`: standalone 7개 → `s_4535.bin`의 런타임 엔트리 1개

이 15개 standalone 경로는 4개의 동일 payload 그룹이다. 후속 빌더는 파일명이나 standalone 경로 하나만으로 수정 대상을 고르지 말고, 대응표의 런타임 키를 사용해야 한다. 같은 payload를 공유하는 번역 레코드가 서로 다른 번역을 요구하면 자동 병합하지 않고 충돌로 중단해야 한다.

## 할당 공간

- 기존 할당 여유가 0바이트인 런타임 XSO: 0개
- 현재 압축 크기가 할당 공간의 90% 이상인 엔트리: 1개
- 해당 엔트리: `PSP_GAME/USRDIR/data/arc/s_0551.bin#8:s_0551.xso.z`
- 원본 압축 크기: 1,946바이트
- 할당 크기: 2,048바이트
- 원본 여유: 102바이트

계획 019의 최종 번역본은 1,964바이트로 84바이트가 남았지만, 이번 표는 원본 ISO를 기준으로 하므로 원본 수치 1,946/2,048바이트를 기록한다. 현재 여유 공간은 번역 후 압축 크기를 보장하지 않으며, 실제 번역을 적용한 뒤 엔트리별로 다시 검사해야 한다.

## 회귀 및 재현성 검증

- `s_0551` payload SHA-256 `1BA1D501FEF350045691CA15F3A4F99205623C829F3B916FEA566E3978175614` 대응 재검출 성공
- 동일 입력으로 두 번 실행한 JSON·CSV·Markdown 산출물 바이트 단위 일치
- JSON 대응 그룹: 1,106개
- 아카이브 CSV: 222행
- 대응 CSV: 1,106행
- 할당 CSV: 344행
- CSV 3종 UTF-8 BOM 확인
- 단위 테스트 포함 전체 테스트 58건 통과
- Python 바이트코드 컴파일 통과
- 분석 전후 원본 ISO SHA-256 동일

원본 ISO SHA-256:

`0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B`

## 산출물

- JSON 정본: `/.work/ys6-runtime-archive-map/runtime_archive_xso_map.json`
- 아카이브 목록: `/.work/ys6-runtime-archive-map/archive_inventory.csv`
- XSO 대응표: `/.work/ys6-runtime-archive-map/xso_runtime_mapping.csv`
- 할당 보고서: `/.work/ys6-runtime-archive-map/xso_allocation_report.csv`
- 요약: `/.work/ys6-runtime-archive-map/summary.md`

산출물 SHA-256:

| 파일 | SHA-256 |
|---|---|
| `runtime_archive_xso_map.json` | `1BDE7809793363F57E43B989A35A2FE22784EE796E1A9645310D725EB84AC017` |
| `archive_inventory.csv` | `B6C2B6CDE59009A89B4F65ECAAE173F5D8D9654F2612A0C8D082A0B3EE60DDF5` |
| `xso_runtime_mapping.csv` | `9AE50893E284320AF4FEDFEACAF9FFE7ADB7583F6E7743687EFC99C73F516138` |
| `xso_allocation_report.csv` | `D3AF730A2B3D9E7CAC88324249BAECA91709B4C18E0BC4E978DF50FB7EEB2977` |
| `summary.md` | `7413BF488B1B723CBF0EEECB7F0C8C753AB3042376B6C778917FC1660C53EC4E` |

## 알려진 제한

- `/data/arc`만 분석했으므로 standalone 미대응 839개가 실제로 미사용이라고 단정할 수 없다.
- 파일명과 맵 ID가 유사하더라도 payload 해시가 다르면 자동 대응하지 않았다.
- 대응표는 원본 일본어 payload 기준이다. 번역으로 XSO 해시가 바뀐 뒤에는 원본 해시를 식별 키로 유지해야 한다.
- 할당 여유 합계만으로 아카이브 재배치 가능성을 판단할 수 없다. 엔트리 순서, 정렬 및 테이블 크기를 함께 다뤄야 한다.

## 다음 단계 권고

다음은 `021 다중 XSO·런타임 아카이브 통합 빌더`가 적절하다.

우선 기존 할당 안에 들어가는 번역만 대상으로 다음 파이프라인을 구현한다.

1. 검수 완료 번역을 원본 XSO SHA-256별로 그룹화
2. 020 대응표에서 확정 런타임 키 조회
3. 동일 payload를 공유하는 번역의 충돌 검사
4. 여러 XSO 재조립·압축 및 엔트리별 할당 사전 검사
5. 여러 아카이브 작업본 생성
6. EBOOT 글리프 집합과 아카이브 변경을 하나의 ISO에 일괄 반영
7. 허용 범위 밖 ISO 변경 0건 검증

할당을 초과하는 XSO는 수정하지 않고 목록으로 보고한다. 아카이브 전체 재배치는 021 결과에서 실제 초과 사례와 필요한 범위를 확보한 뒤 별도 계획으로 분리하는 것이 안전하다.

## 정리

이번 작업은 읽기 전용으로 수행했으며 `/patched`에 새 ISO를 생성하지 않았다. 재현성 검증용 두 번째 분석 디렉터리는 비교 후 삭제했고 정본 산출물 한 세트만 유지했다. 원본 ISO와 기존 019 패치 ISO는 변경하지 않았다.
