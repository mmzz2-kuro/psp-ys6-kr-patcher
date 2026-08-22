# 091. Ys VI 엔딩 메시지 v130~v132 한글 이미지 패치 결과

## 수행 내용

- `v130.dds.z`~`v132.dds.z` 엔딩 메시지 세 장을 승인된 문안으로 한글화했다.
- 480×64 합성 이미지를 원래 `256+128+64+32` picture 경계로 다시 인코딩했다.
- 각 picture의 선행 16바이트 표시 오프셋을 보존했다.
- `v130`의 첫 picture는 원본 RGBA8888로, 나머지 picture는 원본 DXT1 형식으로 처리했다.
- 독립 원본 세 개와 `s_0002.bin` 실행 복제본 세 개를 추가 이미지 패치에 등록했다.
- `p901`, `p902`는 PS2판 치트 안내이므로 번역·패치 대상에서 제외했다.

## 적용 번역

| 리소스 | 적용 문구 |
|---|---|
| `v130` | `수많은 인과를 집어삼켜 온 / 숙업의 소용돌이는 이제 사라지고.` |
| `v131` | `바다도, 하늘도, 끝없이 푸르게 펼쳐져 있었다.` |
| `v132` | `새로운 세계의 막이 오르고―― / 지금 다시, 아돌의 모험이 시작된다.` |

## 변경·생성 파일

- 추가: `tools/scripts/ys6_ending_message_localize.py`
- 변경: `tools/scripts/ys6_additional_image_patch.py`
- 변경: `tools/patchdata/ys6_additional_images/manifest.json`
- 생성: `tools/patchdata/ys6_additional_images/source_images/ending_messages/v130.png`~`v132.png`
- 생성: `tools/patchdata/ys6_additional_images/source_parts/ending_message_v130/message.png` 등 3개
- 생성: `tools/patchdata/ys6_additional_images/edited_parts/ending_message_v130/message.png` 등 3개
- 생성: `tools/patchdata/ys6_additional_images/ending-message-preview-2x.png`
- 생성: `tools/patchdata/ys6_additional_images/ending-message-localize-report.json`
- 갱신: `tools/patchdata/ys6_additional_images/precompiled/manifest.json`
- 추가: `tools/patchdata/ys6_additional_images/precompiled/ending_message_v130.dds.z` 등 3개
- 완료 갱신: `docs/plan/091-ys6-ending-message-v130-v132-korean-image-patch.md`

## 증분 캐시 결과

- 기존 캐시 재사용: 46개
- 재압축: 0개
- 신규 생성: 3개
- 제거: 0개
- 전체 캐시: 49개, 859,625바이트
- 갱신 소요 시간: 4.451초

| 리소스 | 압축 크기 | 원본 할당 공간 |
|---|---:|---:|
| `ending_message_v130` | 3,872 | 6,144 |
| `ending_message_v131` | 1,457 | 2,048 |
| `ending_message_v132` | 1,777 | 4,096 |

세 컨테이너 모두 원본 ISO 할당 공간 안에 들어간다.

## 사전 검증 및 테스트 ISO

- GUI 공통 빌더 사전 검증: 성공
- 테스트 ISO 생성: 성공
- 추가 이미지 리소스: 49개
- 독립 이미지 교체 수: 88개
- 실행 복제본 등록/교체: 70/70개
- 신규 실행 복제본 `s_0002.bin` index 26~28: 3/3 캐시 컨테이너와 일치
- 테스트 ISO에서 `v130`~`v132` 재추출·합성: 3/3 성공
- 재추출 이미지의 한글 문장, 중앙 배치와 picture 경계: 정상
- 기존 관련 단위 테스트: 12개 통과
- 오버플로: 없음
- 테스트 ISO SHA-256: `7CD36C58BC76CE121E6F88122A96AB5262386B750A21669CB891684BDD13F34E`

## 테스트 ISO와 확인 파일

- 테스트 ISO: `patched/091-ys6-ending-message-v130-v132-korean-image-patch/Ys VI (Japan) - 091-ending-message-korean-test.iso`
- 한글 미리보기: `tools/patchdata/ys6_additional_images/ending-message-preview-2x.png`
- 테스트 ISO 재추출 결과: `tools/patchdata/work/current/091-ending-message-patched-verification`

원본 ISO는 변경하지 않았다. 재추출 결과와 테스트 ISO는 이슈 완료 후 정리 가능한 검증 산출물이다.

## 알려진 사항

- 파일·아카이브·캐시 수준 검증은 완료했다.
- 실제 게임 엔딩 장면에서는 표시 시간, 화면 중앙 배치와 PSP 해상도 가독성을 최종 확인해야 한다.
