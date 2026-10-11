# 119. Ys VI PSP 실기 엔딩 한글 PMF 프리징 수정 결과

상태: 완료

## 결과

- 한글 자막이 합성된 `im03a_kaizoku.pmf`, `im03b_kazaminooka.pmf`가 PSP 실기에서 끝까지 정상 재생됐다.
- 사용자가 두 영상의 한글 자막 출력, 영상 진행 및 종료를 실기에서 확인했다.
- 실기 검증본을 정식 패치 도구의 엔딩 영상 자산으로 반영했다.
- GUI의 기존 `엔딩 영상 적용` 옵션은 변경 없이 새 자산을 사용한다.

## 원인과 해결

### 기존 프리징

- 096번 PMF는 교체 H.264 AU가 원본보다 작을 때 대량의 후행 `0x00`을 넣어 원본 AU 크기를 유지했다.
- PC 디코더와 PPSSPP에서는 통과했지만 PSP 실기에서는 첫 한글 자막 구간에서 멈췄다.
- ISO는 2,048바이트 논리 섹터 기반이므로 CD raw-sector EDC/ECC 누락이 원인은 아니었다.

### 검은 화면 시험본

- 영상 전용으로 완전히 재멀티플렉싱한 PMF에는 원본의 `0xBD` private stream이 없었다.
- 이 시험본은 PSP에서 엔딩 영상 재생 자체가 시작되지 않았다.

### 최종 방식

- pmftools-plus로 PSP 형식의 영상 팩을 생성했다.
- 원본 PMF의 `0xBD` private-stream 팩을 바이트 단위로 보존했다.
- 각 팩의 SCR을 읽어 새 영상 팩과 원본 private-stream 팩을 시간순으로 병합했다.
- 원본 PSMF 헤더를 기반으로 본문 크기를 갱신하고, 원본 ISO 할당 범위 안에 배치했다.

## 정식 자산

| 파일 | 크기 | SHA-256 | 원본 private 팩 |
|---|---:|---|---:|
| `im03a_kaizoku.pmf` | 11,649,024 | `D11A73DA020B83B3D479DB3F1EAC21FAA1443E88990FFCFA0A1108BA0B3F7D0D` | 660 |
| `im03b_kazaminooka.pmf` | 10,713,088 | `FF43644A13016362FF0DADA85D627C9A09B3E6190726BA6D05AAD5DB94F1A8EE` | 612 |

- 자산 경로: `tools/patchdata/ys6_ending_movies`
- 매니페스트에 병합 방식, 출력 크기·해시, 보존 팩 수 및 PSP 실기 검증일을 기록했다.

## 생성·변경 파일

- `tools/scripts/ys6_pmf_hardware_audit.py`
- `tools/scripts/ys6_pmf_av_pack_merge.py`
- `tools/scripts/ys6_pmf_ps_padding_rebuild.py` — 원인 분리용 실험 스크립트이며 정식 빌드에서는 사용하지 않는다.
- `tools/patchdata/ys6_ending_movies/im03a_kaizoku.pmf`
- `tools/patchdata/ys6_ending_movies/im03b_kazaminooka.pmf`
- `tools/patchdata/ys6_ending_movies/manifest.json`
- `docs/plan/119-ys6-real-psp-ending-pmf-freeze-diagnosis.md`

## 검증

- 두 최종 PMF의 영상 전체 FFmpeg 디코딩: 성공
- `im03a` 프레임 수: 2,458, 원본 할당 여유: 137,216바이트
- `im03b` 프레임 수: 2,278, 원본 할당 여유: 61,440바이트
- 통합 패치 사전 빌드: `valid: true`, 엔딩 영상 2개 인식, overflow 없음
- `--no-ending-movies` 사전 빌드: `valid: true`, 엔딩 영상 0개, overflow 없음
- PSP 실기: 두 자막 영상 정상 재생 확인

## 시험 ISO 정리 대상

다음 파일들은 진단 과정의 시험본이며 정식 자산이 아니다. 사용자 확인 후 삭제할 수 있다.

- `patched/119-real-psp-ending-freeze/Ys VI Korean - PSP-native full-remux ending test.iso` — private stream 누락으로 검은 화면
- `patched/119-real-psp-ending-freeze/Ys VI Korean - PSP-mux original-private-stream test.iso` — 실기 검증 완료 시험본
- 같은 폴더의 이전 HRD·원본 대조 시험 ISO가 남아 있다면 함께 정리 가능

## 알려진 사항

- `.work` 및 `tools/patchdata/work/current/119-real-psp-ending-freeze`의 중간 인코딩·분석 파일은 재현 자료로 유지했다.
- 정식 빌드에 사용되는 것은 `tools/patchdata/ys6_ending_movies`의 두 PMF와 매니페스트뿐이다.
