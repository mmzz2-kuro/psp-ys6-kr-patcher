# 076. Ys VI 보스명 이미지 조사 및 패치 작업공간 결과

## 수행 내용

- `boss00.dds.z`, `boss01.dds.z`에서 보스 칭호·이름 8행을 확인했다.
- 각 텍스처를 256×64 크기의 네 행으로 분할해 원본 작업 조각을 생성했다.
- 확정 번역으로 한글 수정 조각 8개를 생성했다.
- 독립 이미지 두 개와 실제 게임에서 사용하는 아카이브 복제본 8개를 추가 이미지 패치 매니페스트에 등록했다.
- 기존 GUI의 `추가 이미지 적용` 선택이 해당 리소스들의 사전검증과 ISO 패치 적용을 함께 제어하도록 기존 공통 경로에 편입했다.

## 확정 번역

| 칭호 | 보스명 |
|---|---|
| 떠돌이 용 | 데미갈바 |
| 탐욕스러운 날개 | 존프라스 |
| 창람의 수호자 | 우드＝메이유 |
| 공허한 포효 | 오쥬간 |
| 혼돈의 사냥꾼 | 라나루나 |
| 용신병 완전체 | 갈바로아 |
| 검은 열쇠의 계승자 | 에른스트 |
| 외해 기구 | 나피쉬팀 |

## 런타임 복제본

- `boss_names_00`: `s_0699#index 54`, `s_2099#index 94`, `s_5399#index 68`, `s_5599#index 106`
- `boss_names_01`: `s_4699#index 69`, `s_7199#index 40`, `s_7499#index 104`, `s_7599#index 83`

모든 복제본은 조사 당시 독립 리소스와 컨테이너 및 압축 해제 payload SHA-256이 일치했다.

## 생성·변경 파일

- 변경: `tools/patchdata/ys6_additional_images/manifest.json`
- 추가: `tools/scripts/ys6_boss_name_localize.py`
- 추가: `tools/patchdata/ys6_additional_images/source_images/boss00.png`
- 추가: `tools/patchdata/ys6_additional_images/source_images/boss01.png`
- 추가: `tools/patchdata/ys6_additional_images/source_parts/boss_names_00/line_01.png` ~ `line_04.png`
- 추가: `tools/patchdata/ys6_additional_images/source_parts/boss_names_01/line_01.png` ~ `line_04.png`
- 추가: `tools/patchdata/ys6_additional_images/edited_parts/boss_names_00/line_01.png` ~ `line_04.png`
- 추가: `tools/patchdata/ys6_additional_images/edited_parts/boss_names_01/line_01.png` ~ `line_04.png`
- 생성: `tools/patchdata/ys6_additional_images/boss-name-localize-report.json`
- 생성: `tools/patchdata/ys6_additional_images/boss_names_00-preview-dark.png`
- 생성: `tools/patchdata/ys6_additional_images/boss_names_01-preview-dark.png`

## 검증 결과

- 추가 이미지 작업공간 검사: 성공, 수정 이미지 52개 중 보스명 8개 인식
- GUI 공통 빌더 사전검증: 성공
- 보스명 리소스 수: 2
- 적용 영역: 각 4개, 총 8개
- `boss_names_00`: 변경 DXT3 블록 1,447개, 컨테이너 1,789/8,192바이트, 잔여 6,403바이트
- `boss_names_01`: 변경 DXT3 블록 1,456개, 컨테이너 1,775/8,192바이트, 잔여 6,417바이트
- 런타임 복제본: 8/8 교체 검증 성공
- 전체 추가 이미지 런타임 복제본: 49/49 교체 검증 성공
- 할당 공간 초과: 없음

## 알려진 사항

- 한글 이미지는 프로젝트의 기존 대사 글꼴과 같은 Gulim Regular를 사용해 결정론적으로 생성했다.
- 흰색 글자와 알파 채널로 구성된 게임 텍스처이므로 일반 흰 배경 이미지 뷰어에서는 글자가 보이지 않을 수 있다. 확인용 어두운 배경 미리보기를 함께 생성했다.
- 이번 작업에서는 ISO를 새로 생성하지 않았다. GUI에서 `추가 이미지 적용`을 선택한 다음 빌드하면 포함된다.
- 새 임시 ROM 및 삭제 대상 ROM은 없다.
