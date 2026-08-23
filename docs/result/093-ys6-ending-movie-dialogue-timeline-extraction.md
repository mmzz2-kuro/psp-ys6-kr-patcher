# 093. Ys VI 엔딩 영상 대사·타임코드 추출 결과

## 결과

- `im03a_kaizoku.pmf`에서 10개, `im03b_kazaminooka.pmf`에서 5개 대사를 확인했다.
- 두 영상의 29.97fps(`30000/1001`) 원본 프레임 번호를 기준으로 시작·종료 구간을 기록했다.
- PMF 비디오 스트림의 시작 PTS 1.0초를 반영한 PTS 값과 영상 상대 타임코드를 함께 기록했다.
- 각 대사의 완성된 문구가 가장 선명한 프레임을 대표 프레임으로 선택하고 대화창 부분 이미지도 별도로 추출했다.
- 0.5초 간격 검수 시트와 대사별 대표 이미지 접촉 시트를 생성했다.

## 번역 데이터 대조

- 15개 대사 전부 `tools/config/dialogue-translations.json`의 기존 `override` 번역과 연결됐다.
- 8개는 원문 그대로 일치했다.
- 5개는 영상의 실제 줄바꿈과 설정 파일의 `\\n` 표기를 정규화하면 일치한다.
- 2개는 설정 파일의 `\\x1` 인물명 변수가 영상에서 `アドル`로 치환된 경우다.
- 출력물의 번역은 후속 영상 합성 시 기준을 잃지 않도록 현재 설정 파일 값을 그대로 보존했다.

현재 번역 데이터에는 `저 안에아돌이`의 띄어쓰기와 이샤의 말줄임표 끝에 붙은 ASCII 마침표처럼 후속 자막 작성 전에 재검토할 만한 표현이 있다. 이번 작업에서는 원본 번역 설정을 변경하지 않았다.

## 생성·변경 파일

- `tools/scripts/ys6_movie_dialogue_timeline.py`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/dialogue-timeline.json`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/im03a_kaizoku-dialogues.csv`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/im03b_kazaminooka-dialogues.csv`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/im03a_kaizoku-dialogue-contact-sheet.png`
- `tools/patchdata/work/current/093-ending-movie-dialogue-timeline/im03b_kazaminooka-dialogue-contact-sheet.png`
- 같은 출력 폴더 아래의 `representative_frames`, `dialogue_crops`, `review_sheets`
- `docs/plan/093-ys6-ending-movie-dialogue-timeline-extraction.md` 상태 갱신
- `docs/result/093-ys6-ending-movie-dialogue-timeline-extraction.md`

## 검증

- 두 PMF를 순차 디코딩해 임의 탐색 시 발생할 수 있는 H.264 프레임 손상을 피했다.
- 대화별 시작 프레임이 종료 프레임보다 빠른지, 다음 대화와 순서가 뒤집히거나 겹치지 않는지 검사했다.
- 15개 번역 참조 SHA-256이 모두 현재 번역 설정에 존재하며 출력 번역과 동일한지 검사했다.
- 스크립트를 `python -m py_compile`로 검사했다.
- 대표 접촉 시트를 육안 확인해 각 항목의 인물명과 완성 문구가 식별되는지 확인했다.

## 범위 밖 및 다음 단계

- 영상 프레임 수정, 한글 자막 합성, 재인코딩, PMF 재구성 및 ISO 적용은 수행하지 않았다.
- 다음 단계에서는 현재 번역 문구를 영상 자막용으로 교정한 뒤, 대화창 자체를 한글화할지 별도 자막을 덧씌울지 결정해야 한다.
- 이번 작업에서 별도의 테스트 ISO나 임시 ROM은 생성하지 않았다.
