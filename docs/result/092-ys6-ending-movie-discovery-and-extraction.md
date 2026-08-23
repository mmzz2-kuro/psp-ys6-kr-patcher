# 092. Ys VI 최종 보스 이후 동영상 탐색·추출 결과

## 정정 결론

- 원본 ISO의 PMF 영상 11개를 모두 다시 확인했다.
- 일본어 대화창이 영상 프레임에 직접 들어간 파일은 총 3개다: `demo9.pmf`, `im03a_kaizoku.pmf`, `im03b_kazaminooka.pmf`.
- 사용자가 확인한 대상은 `demo9.pmf`가 아니므로, **실제 엔딩 계열 후보는 나머지 두 개**다.
  - `im03a_kaizoku.pmf`: 나피쉬팀 붕괴 연출 뒤 해적선에서 이어지는 PC판 대화 장면
  - `im03b_kazaminooka.pmf`: 재해 소멸 연출 뒤 바람개비언덕에서 이어지는 PC판 대화 장면
- 두 영상 모두 일본어 대화창과 초상화가 영상 픽셀에 합성되어 있어 별도 대사 데이터로 교체할 수 없다.

## 엔딩 계열 후보 정보

| 항목 | `im03a_kaizoku.pmf` | `im03b_kazaminooka.pmf` |
|---|---:|---:|
| ISO 경로 | `PSP_GAME/USRDIR/data/movie/im03a_kaizoku.pmf` | `PSP_GAME/USRDIR/data/movie/im03b_kazaminooka.pmf` |
| 원본 크기 | 11,786,240바이트 | 10,774,528바이트 |
| SHA-256 | `ACD6DD575DCA3CA61250A11AC90C92A4E7838B8575CB883E9F7A9FF162255932` | `90795FC39BE37F51901FE0DCEF4A6DF2C9DA0970EF45C46297A84F64393CE103` |
| 재생 시간 | 약 81.782초 | 약 75.943초 |
| 영상 | H.264/AVC, 480×272, 약 29.97fps | H.264/AVC, 480×272, 약 29.97fps |
| 일본어 장면 | 후반 해적선 대화 | 후반 바람개비언덕 대화 |

## 전체 영상 분류

| 영상 | 판정 |
|---|---|
| `demo8.pmf` | 최종 보스 전투 짧은 연출, 확인 프레임에 대화창 없음 |
| `demo9.pmf` | PC판 실내 대화 녹화 영상이나 사용자 확인 대상 아님 |
| `ending.pmf` | 정식 엔딩 영상, 영어 로고 외 일본어 대화창 없음 |
| `im01.pmf` | 섬·함선 연출, 대화창 없음 |
| `im02.pmf` | 해저·함선·재해 연출, 대화창 없음 |
| `im03a.pmf` | 나피쉬팀 붕괴 연출만 포함 |
| `im03a_kaizoku.pmf` | `im03a` 연출과 해적선 PC판 일본어 대화 포함 |
| `im03b.pmf` | 재해 소멸 연출만 포함 |
| `im03b_kazaminooka.pmf` | `im03b` 연출과 바람개비언덕 PC판 일본어 대화 포함 |
| `logo.pmf` | Falcom 로고 |
| `opening.pmf` | 오프닝 영상 |

`_kaizoku`와 `_kazaminooka` 버전은 각각 기본 `im03a`, `im03b`보다 길며 후반에 PC판 게임 화면과 대화창이 추가되어 있다.

## 추출 산출물

- 원본 PMF:
  - `tools/patchdata/work/current/092-ending-movie-discovery/im03a_kaizoku.pmf`
  - `tools/patchdata/work/current/092-ending-movie-discovery/im03b_kazaminooka.pmf`
- PC 확인용 무재인코딩 MP4:
  - `im03a_kaizoku-video-only.mp4`
  - `im03b_kazaminooka-video-only.mp4`
- 2초 간격 전체 확인 시트:
  - `im03a_kaizoku-contact-2s-01.png`, `02.png`
  - `im03b_kazaminooka-contact-2s-01.png`, `02.png`
- 전체 PMF 11개와 해시: `tools/patchdata/work/current/092-ending-movie-discovery/extract-report.json`

## 변경·생성 파일

- 추가: `tools/scripts/ys6_movie_extract.py`
- 생성: `tools/patchdata/work/current/092-ending-movie-discovery/*`
- 완료 갱신: `docs/plan/092-ys6-ending-movie-discovery-and-extraction.md`
- 정정: `docs/result/092-ys6-ending-movie-discovery-and-extraction.md`

## 검증

- 원본 ISO의 PMF 11개 무손실 추출: 성공
- 모든 파일의 `PSMF0012` 매직 확인
- 11개 영상의 10초 간격 대표 프레임 확인
- 엔딩 후보 두 개는 추가로 2초 간격 전체 프레임 확인
- 두 후보의 H.264 스트림 복사 MP4 생성: 성공
- 일본어 대화창이 별도 자막 스트림이 아니라 영상 픽셀에 포함된 것 확인
- 원본 ISO와 기존 패치 ISO는 변경하지 않았다.

## 후속 한글화 권장 방식

1. 두 후보 중 실제 게임에서 재생되는 범위를 확인한다. 두 영상이 연속 재생된다면 모두 작업 대상으로 잡는다.
2. 후반 PC판 대화 구간의 정확한 시작·종료 타임코드와 표시 문장을 프레임 단위로 추출한다.
3. 기존 번역 데이터에서 같은 원문 대사를 찾아 한국어 문안을 재사용한다.
4. 일본어 대화창 부분을 한국어 대화창으로 프레임에 다시 합성한다.
5. 480×272, 29.97fps의 PSP 호환 H.264로 인코딩하고 PMF/PSMF 컨테이너로 재구성한다.
6. 각 원본 파일의 할당 공간 안에 맞춰 ISO에 교체하고 실제 재생을 검증한다.

## 알려진 사항

- 현재 FFmpeg는 세 PMF에서 H.264 영상만 인식하며 별도 음성·자막 스트림은 표시하지 않는다.
- 생성한 MP4는 영상 확인용이며 PMF 교체본으로 바로 사용할 수 없다.
- 실제 게임이 두 엔딩 후보를 모두 순서대로 재생하는지는 게임 플레이 또는 호출 흐름 추적으로 최종 확인해야 한다.
