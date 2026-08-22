# 082. Ys VI 제메스의 성지 석상 메시지 한글 이미지 패치 결과

## 수행 내용

- `v100`~`v107` 석상 메시지 8개를 승인된 한국어 문구로 제작했다.
- 점 전환 표시인 `v108`은 원본 이미지를 그대로 유지했다.
- 9개 모두 256×64 RGBA 편집 이미지로 준비했다.
- 흰 글자, 검은 외곽선 및 투명 배경을 유지했다.
- 문구 길이에 따라 13~18픽셀 글꼴 크기를 자동 적용해 256픽셀 폭 안에 배치했다.
- 추가 이미지 매니페스트에 9개 리소스를 등록했다.
- 독립 원본 9개와 `s_6600.bin` 내부 실행 복제본 8개를 패치 대상으로 연결했다.
- GUI 추가 이미지 캐시를 36개 리소스로 갱신했다.

## 적용 번역

| 리소스 | 적용 문구 |
|---|---|
| `v100` | `……잘 왔도다……` |
| `v101` | `내 이름은 알마…… / 위대한 《상자》를 봉인한 자……` |
| `v102` | `내 육신은 이곳에서 스러질지라도 / 그 혼은 후손들에게 이어지리라……` |
| `v103` | `검사여…… / 머나먼 땅에서 동포들을 구한 자여……` |
| `v104` | `마지막 《열쇠》를 그대에게 맡기리라……` |
| `v105` | `검사여……명심하라……` |
| `v106` | `……빼앗긴 《검은 열쇠》가 / 《상자》의 뚜껑을 열려 하고 있다……` |
| `v107` | `……사악한 꿈이……되살아나기 전에……` |
| `v108` | 원문 점 전환 표시 유지 |

## 변경·생성 파일

- 추가: `tools/scripts/ys6_zemes_statue_message_localize.py`
- 변경: `tools/patchdata/ys6_additional_images/manifest.json`
- 생성: `tools/patchdata/ys6_additional_images/source_parts/zemes_statue_v100/message.png` ~ `zemes_statue_v108/message.png`
- 생성: `tools/patchdata/ys6_additional_images/edited_parts/zemes_statue_v100/message.png` ~ `zemes_statue_v108/message.png`
- 생성: `tools/patchdata/ys6_additional_images/zemes-statue-message-preview.png`
- 생성: `tools/patchdata/ys6_additional_images/zemes-statue-message-localize-report.json`
- 갱신: `tools/patchdata/ys6_additional_images/precompiled/manifest.json`
- 갱신: `tools/patchdata/ys6_additional_images/precompiled/*.dds.z`
- 완료 갱신: `docs/plan/082-ys6-zemes-statue-message-korean-image-patch.md`
- 생성: `docs/result/082-ys6-zemes-statue-message-korean-image-patch.md`

## 캐시 및 압축 검증

- 전체 추가 이미지 캐시: 36개
- GUI 공통 빌더 사전 검증 캐시 사용: 36/36개
- 새 리소스 압축 크기와 할당 공간:

| 리소스 | 압축 크기 | 할당 공간 |
|---|---:|---:|
| `v100` | 1,129 | 2,048 |
| `v101` | 3,077 | 6,144 |
| `v102` | 3,413 | 8,192 |
| `v103` | 2,465 | 6,144 |
| `v104` | 1,840 | 4,096 |
| `v105` | 1,560 | 4,096 |
| `v106` | 3,390 | 6,144 |
| `v107` | 1,721 | 4,096 |
| `v108` | 1,244 | 2,048 |

모든 리소스가 원본 할당 공간 안에 들어간다.

## ISO 검증

- GUI 공통 빌더 사전 검증: 성공
- 테스트 ISO 생성: 성공
- 테스트 ISO SHA-256: `8ABACC2D20E3284AF20738C9637579D6DF08BF2F3EBC70D2CEDE54472FF6F78F`
- 독립 원본 `v100`~`v108`과 캐시 결과 해시: 9/9 일치
- `s_6600.bin` 인덱스 143~150과 캐시 결과 해시: 8/8 일치
- 테스트 ISO에서 재추출 및 DXT3 디코딩: 9/9 성공
- 재추출 미리보기에서 잘림, 행 겹침 및 불투명 배경: 없음
- Python 구문 검사: 성공

## 테스트 ISO

- 경로: `patched/082-ys6-zemes-statue-message-korean-image-patch/Ys VI (Japan) - 082-zemes-statue-korean-test.iso`
- 용도: 제메스의 성지 석상 메시지 한글 출력 실기 확인
- 원본 ISO는 변경하지 않았다.

## 확인용 파일과 임시 파일

- 최종 한글 미리보기: `tools/patchdata/ys6_additional_images/zemes-statue-message-preview.png`
- 테스트 ISO 재추출 결과: `tools/patchdata/work/current/082-zemes-patched-verification`
- 재추출 결과는 검증용 임시 파일이며 이슈 완료 후 정리할 수 있다.

## 알려진 사항

- 파일과 아카이브 수준 검증은 완료했다. 실제 게임 화면에서 표시 위치, PSP 해상도 가독성 및 이벤트 전체 순서는 사용자가 테스트 ISO로 최종 확인해야 한다.
- `v108`은 `s_6600.bin` 내부 복제본 없이 독립 원본만 존재하며 원문과 같은 점 전환 표시를 유지했다.
