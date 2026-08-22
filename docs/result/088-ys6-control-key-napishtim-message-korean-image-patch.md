# 088. Ys VI 제어 키·나피쉬팀 메시지 한글 이미지 패치 결과

## 수행 내용

- `v140`, `v141`, `v150`~`v157` 메시지 이미지 10개를 승인된 권장 번역으로 한글화했다.
- 사용자가 제공한 번역의 `기장제어기구` 오타를 `기상 제어 기구`로 바로잡았다.
- `알마`, `엘딘`, `에레시아`, `나피쉬팀` 등 기존 이미지 번역 용어와 통일했다.
- 원문의 흰 글자, 검은 외곽선 및 투명 배경을 유지했다.
- 원본과 같이 대부분 한두 줄로 배치하고 긴 `v156`만 가독성을 위해 3줄로 배치했다.
- 추가 이미지 매니페스트에 독립 원본 10개와 실행 복제본 10개를 등록했다.
- GUI 증분 캐시 갱신으로 기존 36개를 재사용하고 신규 10개만 압축했다.

## 적용 번역

| 리소스 | 적용 문구 |
|---|---|
| `v140` | `제어 키의 기능 정지를 확인……` |
| `v141` | `지금부터 자동 제어 상태로 이행한다……` |
| `v150` | `나는 아틀라스해 전역을 관리하는 / 기상 제어 기구 《나피쉬팀》……` |
| `v151` | `알마에 의해 봉인된 후 / 나는 깊은 잠 속에서 꿈을 꾸고 있었다……` |
| `v152` | `위대한 엘딘의 황혼과 / 그 씨앗이 에레시아 땅에 뿌리내리는 것을……` |
| `v153` | `하지만 천 년이 지난 지금…… / 모든 것은 수포로 돌아간 것 같다……` |
| `v154` | `이제 에레시아 땅에서 / 엘딘의 정신은 완전히 사라졌다……` |
| `v155` | `거짓 문명은 멸망해야 한다……` |
| `v156` | `역장에 의한 수벽 전개를 종료…… / 에레시아 대륙 서해안 지역을 / 소거할 수 있다……` |
| `v157` | `지금부터 최종 단계로 이행한다……` |

## 변경·생성 파일

- 추가: `tools/scripts/ys6_control_key_message_localize.py`
- 변경: `tools/patchdata/ys6_additional_images/manifest.json`
- 생성: `tools/patchdata/ys6_additional_images/source_parts/control_message_v140/message.png` 등 원본 조각 10개
- 생성: `tools/patchdata/ys6_additional_images/edited_parts/control_message_v140/message.png` 등 한글 이미지 10개
- 생성: `tools/patchdata/ys6_additional_images/control-key-message-preview.png`
- 생성: `tools/patchdata/ys6_additional_images/control-key-message-localize-report.json`
- 갱신: `tools/patchdata/ys6_additional_images/precompiled/manifest.json`
- 추가: `tools/patchdata/ys6_additional_images/precompiled/control_message_v*.dds.z` 10개
- 완료 갱신: `docs/plan/088-ys6-control-key-napishtim-message-korean-image-patch.md`
- 생성: `docs/result/088-ys6-control-key-napishtim-message-korean-image-patch.md`

## 증분 캐시 결과

- 기존 캐시 재사용: 36개
- 재압축: 0개
- 신규 압축: 10개
- 제거: 0개
- 전체 캐시: 46개, 852,519바이트
- 갱신 소요 시간: 13.72초

| 리소스 | 압축 크기 | 할당 공간 |
|---|---:|---:|
| `v140` | 2,244 | 6,144 |
| `v141` | 2,310 | 6,144 |
| `v150` | 4,455 | 10,240 |
| `v151` | 3,950 | 8,192 |
| `v152` | 3,770 | 8,192 |
| `v153` | 3,548 | 8,192 |
| `v154` | 3,453 | 8,192 |
| `v155` | 2,058 | 4,096 |
| `v156` | 5,038 | 8,192 |
| `v157` | 2,313 | 6,144 |

모든 컨테이너가 원본 ISO 할당 공간 안에 들어간다.

## 사전 검증 및 ISO 결과

- GUI 공통 빌더 사전 검증: 성공
- 추가 이미지 캐시 사용: 46/46개
- 신규 실행 복제본 교체: 10/10개
- 테스트 ISO 생성: 성공
- 테스트 ISO SHA-256: `6EDB9951C4DA3B1322EF1F4C157DD8633BC8D1A4CF130D76824551EED3C68F40`
- 독립 원본과 캐시 컨테이너 해시: 10/10 일치
- `s_7499.bin` 실행 복제본과 캐시 해시: 2/2 일치
- `s_7599.bin` 실행 복제본과 캐시 해시: 8/8 일치
- 테스트 ISO에서 DXT3 재추출·렌더링: 10/10 성공
- 재추출 이미지와 최종 미리보기: 일치
- 기존 추가 이미지 36개: 증분 캐시에서 전부 재사용
- Python 구문 검사: 성공

## 테스트 ISO

- 경로: `patched/088-ys6-control-key-napishtim-message-korean-image-patch/Ys VI (Japan) - 088-control-message-korean-test.iso`
- 용도: 제어 키 및 후반 나피쉬팀 메시지의 실제 게임 출력 확인
- 원본 ISO는 변경하지 않았다.

## 확인용 파일과 임시 파일

- 최종 한글 미리보기: `tools/patchdata/ys6_additional_images/control-key-message-preview.png`
- 테스트 ISO 재추출 결과: `tools/patchdata/work/current/088-control-message-patched-verification`
- 재추출 결과는 검증용 임시 파일이며 이슈 완료 후 정리할 수 있다.

## 알려진 사항

- 파일·아카이브·캐시 수준 검증은 완료했다.
- 실제 게임에서는 `s_7499` 제어 키 이벤트와 `s_7599` 후반 이벤트에서 표시 위치, 지속 시간 및 PSP 화면 가독성을 최종 확인해야 한다.
