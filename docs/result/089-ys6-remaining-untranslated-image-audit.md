# 089. Ys VI 잔여 미번역 이미지 전수 점검 결과

## 결론

- 현재 추가 이미지 패치와 옵션 메뉴 패치에 포함되지 않은 일본어 이미지 리소스는 **5개** 확인했다.
- 확정 후보는 `p901.dds.z`, `p902.dds.z`, `v130.dds.z`, `v131.dds.z`, `v132.dds.z`이다.
- 다섯 리소스 모두 독립 원본뿐 아니라 실제 실행 아카이브 `s_0002.bin`에도 동일 payload가 들어 있다.
- 아카이브 내부에만 존재하면서 독립 원본과 다른 일본어 이미지 리소스는 발견되지 않았다.

## 잔여 후보

| 우선순위 | 리소스 | 용도·판정 | 독립 원본 | 실행 복제본 |
|---|---|---|---|---|
| 높음 | `v130.dds.z` | 엔딩 장면 일본어 문장 | `PSP_GAME/USRDIR/data/image/v130.dds.z` | `PSP_GAME/USRDIR/data/arc/s_0002.bin`, index 26 |
| 높음 | `v131.dds.z` | 엔딩 장면 일본어 문장 | `PSP_GAME/USRDIR/data/image/v131.dds.z` | `PSP_GAME/USRDIR/data/arc/s_0002.bin`, index 27 |
| 높음 | `v132.dds.z` | 엔딩 장면 일본어 문장 | `PSP_GAME/USRDIR/data/image/v132.dds.z` | `PSP_GAME/USRDIR/data/arc/s_0002.bin`, index 28 |
| 중간 | `p901.dds.z` | `Congratulations!` 화면의 일본어 치트 모드 안내 | `PSP_GAME/USRDIR/data/image/p901.dds.z` | `PSP_GAME/USRDIR/data/arc/s_0002.bin`, index 31 |
| 중간 | `p902.dds.z` | `Congratulations!` 화면의 다른 일본어 치트 모드 안내 | `PSP_GAME/USRDIR/data/image/p902.dds.z` | `PSP_GAME/USRDIR/data/arc/s_0002.bin`, index 32 |

`p901`과 `p902`의 영어 제목 `Congratulations!`는 기존 방침대로 유지하고 일본어 본문만 번역 대상이다.

## 이미지 구조

- `p901`, `p902`: 각각 picture 8개
  - 본문 영역: `256x256`, `128x256`, `64x256`, `32x256`
  - 하단 영역: `256x16`, `128x16`, `64x16`, `32x16`
  - 가로로 이어 붙인 뒤 한 장으로 편집하고 같은 경계로 다시 분할하는 방식이 적합하다.
- `v130`: picture 4개 (`256x64`, `128x64`, `64x64`, `32x64`)
  - 첫 picture가 비압축 RGBA8888 형식이어서 공용 렌더러에 해당 형식 지원을 추가했고, 일본어 문장이 들어 있음을 확인했다.
- `v131`, `v132`: 각각 picture 4개 (`256x64`, `128x64`, `64x64`, `32x64`)
  - 가로 결합 후 편집·재분할하는 방식이 적합하다.

## 전수 점검 결과

- 기존 독립 이미지 인벤토리:
  - 이미지 레코드 1,170개
  - 렌더링 성공 881개
  - 접촉 시트 28장 시각 확인
- 아카이브 DDS 점검:
  - 실행 DDS 엔트리 862개
  - 독립 원본 payload와 일치 861개
  - 실행 전용 고유 payload 1개
- 유일한 실행 전용 payload:
  - `PSP_GAME/USRDIR/data/arc/s_9011.bin#97:caution!.dds.z`
  - `32x32`, 16비트 아이콘 성격이며 일본어 텍스트 이미지가 아니다.
- `t*.dds.z` 계열은 이벤트 인물·연출 텍스처이며 번역할 문자가 없었다.
- `v122`, `v123`, `v133` 등 영어 로고·엔딩 표기는 영어 유지 대상으로 분류했다.
- 저장·상점·아이템·검 강화·지역명·월드맵·보스명·타블라스·제메스 석상·제어 키 메시지·옵션 메뉴에서 보인 일본어는 기존 패치 처리 항목과 일치했다.

## 생성·변경 파일

- 추가: `tools/scripts/ys6_untranslated_image_audit.py`
- 변경: `tools/scripts/ys6_mig_collection_extract.py` (비압축 RGBA8888 picture 렌더링 지원)
- 생성: `tools/patchdata/work/current/089-untranslated-image-audit/audit.json`
- 완료 갱신: `docs/plan/089-ys6-remaining-untranslated-image-audit.md`
- 생성: `docs/result/089-ys6-remaining-untranslated-image-audit.md`

## 검증

- 조사 스크립트 Python 구문 검사: 성공
- 원본 ISO 읽기 전용 실행: 성공
- 실행 아카이브 전체 DDS 엔트리 분석: 성공
- 후보 5개 독립 원본/실행 복제본 SHA-256 payload 일치: 확인
- 원본 ISO, 편집 PNG, 추가 이미지 매니페스트, 사전 컴파일 캐시 및 패치 ISO는 변경하지 않았다.

## 후속 권장 묶음

- 다음 이미지 번역 작업은 `v130`~`v132` 엔딩 문장 3개와 `p901`·`p902` 치트 안내 2개를 한 이슈로 묶는 것이 적절하다.
- 번역 전 먼저 각 다중 picture를 원래 배치대로 합친 원본 미리보기를 만들고 문장 판독과 용어를 확정해야 한다.

## 알려진 사항

- 이번 점검은 ISO 내부 리소스와 실행 아카이브 기준이다. 게임 플레이의 모든 분기에서 실제 표시를 재현하는 동적 검증은 하지 않았다.
- `v130` 첫 picture의 비압축 RGBA8888 렌더링은 확인했지만, 후속 편집 시 네 picture의 정확한 화면 결합 순서는 별도로 검증해야 한다.
