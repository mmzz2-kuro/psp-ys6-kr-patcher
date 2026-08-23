# 094. Ys VI 엔딩 영상 한글 대사·화자명 교정 결과

## 결과

- 093번에서 추출한 엔딩 영상 대사 15개의 한글 문장을 교정했다.
- 화자 9명의 일본어 이름을 `cast-names.json` 기준 한글 이름으로 변경했다.
- 번역 설정, 타임라인 스크립트, CSV 및 통합 JSON을 동일한 내용으로 맞췄다.
- 기존 프레임 범위와 PTS는 변경하지 않았다.

## 최종 화자명

- 라바
- 라독선장
- 도기
- 가슈
- 테라
- 이샤
- 울
- 오드족장
- 오르하

## 최종 교정문

### `im03a_kaizoku`

1. 라바: `오오…… / '나피쉬팀의 상자'가!`
2. 라독선장: `위험해…… / 너무 가까이 가면 휘말릴 거야.`
3. 도기: `어이, 검은 머리 애송이!`
4. 도기: `저 안에 아돌이 / 있다는 게 정말이야!?`
5. 가슈: `그래…… 사실이야……`
6. 가슈: `미안하다. 내가 부탁하는 바람에……`
7. 테라: `그, 그럴 수가…… / 이건 너무하잖아!`
8. 테라: `왜 언제나 / 아돌만 위험한 일을 겪는 거야……`
9. 이샤: `…………………………………`
10. 이샤: `…………아……………………`

### `im03b_kazaminooka`

1. 울: `우와! / 저게 뭐야? 정말 예쁘잖아!`
2. 오드족장: `오오…… 이게 무슨 일인가……`
3. 오드족장: `오르하, 저 날개는 혹시……`
4. 오르하: `…………네…………………`
5. 오르하: `알마와…… / ……어머니들이에요……………`

문서의 `/` 표시는 실제 데이터에서 `\\n` 줄바꿈이다.

## 공유 원문 정리

`…………………………………` 원문은 설정 파일에 세 번 존재했다. 그중 엔딩 외 레코드 하나에만 ASCII 마침표가 추가돼 있어 공유 원문 번역 충돌 가능성이 있었으므로 세 레코드를 같은 말줄임표로 통일했다. 원문과 번역 의미는 변경되지 않았다.

## 변경 파일

- `tools/config/dialogue-translations.json`
- `tools/scripts/ys6_movie_dialogue_timeline.py`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/dialogue-timeline.json`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/im03a_kaizoku-dialogues.csv`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/im03b_kazaminooka-dialogues.csv`
- 093번 출력 폴더의 대표 프레임, 대화창 크롭 및 접촉 시트
- `docs/plan/094-ys6-ending-movie-korean-dialogue-and-speaker-correction.md`
- `docs/result/094-ys6-ending-movie-korean-dialogue-and-speaker-correction.md`

## 검증

- 영상별 대사 수가 10개와 5개인지 확인했다.
- 첫·마지막 프레임 범위가 각각 `1686~2372`, `1795~2191`로 유지되는지 확인했다.
- 15개 타임라인 번역이 같은 SHA-256을 사용하는 현재 번역 설정과 모두 일치하는지 확인했다.
- 대상 공유 원문 15종에 서로 다른 번역이 남지 않았는지 확인했다.
- 화자명이 모두 `cast-names.json`의 한글 표기에 포함되는지 확인했다.
- `dialogue-translations.json`과 통합 타임라인 JSON을 파싱했다.
- 타임라인 스크립트를 `python -m py_compile`로 검사했다.

## 범위 밖

- PMF 영상과 오디오는 수정하지 않았다.
- 자막 합성, 재인코딩, PMF 재구성 및 ISO 적용은 수행하지 않았다.
- 테스트 ISO나 임시 ROM은 생성하지 않았다.
