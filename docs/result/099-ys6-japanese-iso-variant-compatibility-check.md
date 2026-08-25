# 099. Ys VI 일본판 ISO 변형 호환성 비교 결과

상태: 완료

## 결론

- `Ys 6 - the ark of napishtim [J].iso`는 기존 지원 ISO의 파일명 변경본이나 단순 재덤프가 아니다.
- 기존 지원본은 `ULJM-05009`, 새 ISO는 `ULJM-05155`이며 새 ISO의 XMB 제목에는 `SPECIAL VERSION`이 명시되어 있다.
- 실행 파일, 게임 데이터 아카이브, 맵 리소스와 엔딩 영상까지 다르므로 **현재 한글 패치를 새 ISO에 동일하게 적용할 수 없다.**
- GUI 빌더에 새 ISO를 입력하면 의도대로 `지원하는 원본 ISO의 SHA-256이 아닙니다` 오류로 중단된다.
- 새 ISO 지원은 단순 허용 해시 추가가 아니라 별도의 이식 프로젝트가 필요하다.

## ISO 식별 정보

| 항목 | 기존 지원 ISO | 새 ISO |
|---|---:|---:|
| 파일명 | `Ys VI - Napishtim no Hako (Japan).iso` | `Ys 6 - the ark of napishtim [J].iso` |
| 파일 크기 | 866,254,848바이트 | 711,917,568바이트 |
| SHA-256 | `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B` | `C7BFF86BB7AA9DE025B4717BE34516A3E52D88EF8AD9AA3696F048D4ECCAE1A9` |
| DISC_ID | `ULJM05009` | `ULJM05155` |
| DISC_VERSION | `1.05` | `1.03` |
| 요구 PSP 시스템 버전 | `2.00` | `2.81` |
| XMB 제목 | `Ys -THE ARK OF NAPISHTIM-` | `Ys -THE ARK OF NAPISHTIM- SPECIAL VERSION` |
| ISO 내부 파일 수 | 9,292 | 7,246 |

## 파일 단위 비교

- 같은 경로·같은 payload지만 LBA가 다른 파일: 4,105개
- 같은 경로지만 내용이 다른 파일: 1,376개
- 기존 ISO에만 있는 파일: 3,811개
- 새 ISO에만 있는 파일: 1,765개
- 같은 경로와 같은 LBA까지 유지된 파일: 0개

이는 단순 패딩 제거나 ISO 재정렬 수준이 아니라 파일 구성 자체가 크게 변경된 버전임을 뜻한다.

## 핵심 패치 대상 차이

| 경로 | 기존 크기 | 새 ISO 크기 | 상태 |
|---|---:|---:|---|
| `PSP_GAME/SYSDIR/EBOOT.BIN` | 1,935,840 | 2,071,264 | 내용·크기 다름 |
| `PSP_GAME/USRDIR/data/arc/init.bin` | 1,570,816 | 288,768 | 내용·구조 크게 다름 |
| `PSP_GAME/USRDIR/data/misc/invinfo.dat` | 13,448 | 없음 | 새 ISO의 독립 파일 없음 |
| `PSP_GAME/USRDIR/data/image/static_tex.dds.z` | 665,135 | 558,711 | 내용·크기 다름 |
| `PSP_GAME/USRDIR/data/movie/im03a_kaizoku.pmf` | 11,786,240 | 11,964,416 | 내용·크기 다름 |
| `PSP_GAME/USRDIR/data/movie/im03b_kazaminooka.pmf` | 10,774,528 | 11,100,160 | 내용·크기 다름 |
| `PSP_GAME/PIC0.PNG` | 56,082 | 66,292 | 내용·할당 조건 다름 |

- `EBOOT.BIN`이 달라 현재 한글 글꼴, 시스템 메시지와 실행 코드 패치를 그대로 사용할 수 없다.
- `init.bin` 구조와 크기가 크게 달라 인물명, 아이템, 옵션 메뉴와 추가 이미지의 런타임 복사본 위치를 다시 조사해야 한다.
- 맵 경로 범주에서도 같은 payload는 2,488개뿐이며, 1,067개가 변경되고 기존 전용 3,614개와 새 버전 전용 818개가 확인됐다.
- 엔딩 PMF도 원본 크기와 해시가 달라 현재 고정 길이 교체 자산을 사용할 수 없다.

## 호환성 판정

- 현재 패치 적용: **불가**
- 빌더의 원본 ISO 해시만 추가: **위험하며 불가**
- 기존 패치 ISO에서 수정 파일을 그대로 복사: **불가**
- 별도 지원 가능성: 새 버전의 EBOOT 복호화·폰트 조사, 대사 카탈로그 재생성, 아카이브 매핑, 이미지와 영상 자산 재검증을 처음부터 수행하면 가능성을 검토할 수 있다.

## 생성 파일

- 비교 도구: `tools/scripts/ys6_iso_variant_compare.py`
- 전체 비교 보고서: `tools/patchdata/work/current/099-iso-compatibility/report.json`
- 파일별 비교표: `tools/patchdata/work/current/099-iso-compatibility/files.csv`
- 새 ISO XMB 추출 자료: `tools/patchdata/work/current/099-iso-compatibility/second-xmb`

## 검증

- 두 ISO는 읽기 전용으로 조사했으며 수정하지 않았다.
- 전체 ISO SHA-256과 모든 ISO9660 파일의 payload SHA-256을 비교했다.
- 새 ISO를 현재 패치 빌더의 사전 검증에 입력해 지원 대상 해시가 아님을 확인했다.
- 이번 조사에서는 새 ISO를 기반으로 패치 ISO를 생성하지 않았다.
