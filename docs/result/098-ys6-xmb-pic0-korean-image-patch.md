# 098. Ys VI XMB PIC0 한글 이미지 패치 결과

상태: 완료

## 수행 내용

- PSP XMB의 `PSP_GAME/PIC0.PNG`에 있던 일본어 제목과 소개 문구를 한글로 교체했다.
- 원본 투명 배경과 하단 영문 저작권 문구는 보존했다.
- `PIC1.PNG`, `ICON0.PNG`, `PARAM.SFO`는 변경하지 않았다.
- 최종 한글 PNG를 패치 자산으로 확정하고 원본 해시, 출력 해시, PNG 규격과 ISO 할당 크기 검증을 빌더에 추가했다.
- GUI에 기본 선택된 `XMB 한글 이미지 적용` 체크박스를 추가했다.
- 체크 상태가 데이터 검사, 사전 검증과 실제 ISO 빌드에 동일하게 전달되도록 연결했다.

## 번역 문구

```text
이스 ~나피쉬팀의 상자~
전해지는 「다정함」,
펼쳐지는 「모험심」―.

무대는 대륙의 아득한 서쪽, 바다 끝―.
절해의 외딴섬에서 펼쳐지는
아돌의 새로운 모험!
성장하는 세 자루의 에메라스 검과
다채로운 액션으로 적을 물리치자!
```

## 생성·변경 파일

- `tools/scripts/ys6_xmb_pic0_korean.py`: 한글 PIC0과 PIC1 합성 미리보기 생성
- `tools/scripts/ys6_xmb_image_discovery.py`: ISO XMB 자산 추출·검증
- `tools/patchdata/ys6_xmb/PIC0.PNG`: 최종 패치 자산
- `tools/patchdata/ys6_xmb/manifest.json`: 원본·출력 조건과 해시
- `tools/scripts/ys6_integrated_build.py`: XMB PNG 검증과 ISO 교체
- `tools/scripts/ys6_patch_builder.py`: XMB 자산 선택과 `--no-xmb-image` 옵션
- `tools/ys6_dialogue_viewer.py`: `XMB 한글 이미지 적용` 체크박스
- `patched/098-xmb-pic0-korean/Ys VI (Japan) - 098-xmb-pic0-korean-test.iso`

## 검증 결과

- 최종 `PIC0.PNG`: 310×180 RGBA, 24,180바이트
- 최종 자산 SHA-256: `D04FAD615E2FEB08D298878FD3A114E160FD234BD4E1D147AC11A4D5D7E95EC7`
- ISO 할당 한도 57,344바이트 이내이며 잔여 공간은 33,164바이트이다.
- 적용 사전 검증: `xmb_image_enabled=true`, `xmb_image_count=1`, overflow 없음
- 제외 사전 검증: `xmb_image_enabled=false`, `xmb_image_count=0`, valid
- 전체 패치 테스트 ISO 크기: 866,254,848바이트
- 테스트 ISO SHA-256: `791B9877A7D0B1EC77838FE10E549FB9263B657765A5E167381ED66A77CC95B5`
- 테스트 ISO에서 재추출한 `PIC0.PNG` SHA-256이 최종 자산과 일치했다.
- 재추출한 `PIC1.PNG`, `ICON0.PNG`, `PARAM.SFO`는 원본 SHA-256과 일치했다.
- ISO 빌드 차이 검증에서 허용 범위 밖 변경은 없었다.
- 관련 Python 파일의 문법 검사를 통과했다.

## 알려진 사항

- PNG와 ISO 구조 검증은 완료했으며 PSP 실기 XMB에서의 최종 위치와 가독성은 사용자 확인이 필요하다.
- 098 테스트 ISO는 위 경로의 1개이며 확인 후 불필요하면 삭제할 수 있다.
- 이미지 수정 시 `tools/scripts/ys6_xmb_pic0_korean.py`로 다시 생성하고 `tools/patchdata/ys6_xmb/PIC0.PNG` 및 manifest 해시를 함께 갱신해야 한다.
