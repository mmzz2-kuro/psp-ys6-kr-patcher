# 097. Ys VI PSP XMB 배경 이미지 조사 결과

상태: 완료

## 결론

- PSP XMB에서 ROM을 선택했을 때 표시되는 전체 화면 배경은 `PSP_GAME/PIC1.PNG`이다.
- 배경 위에 표시되는 일본어 게임 설명과 저작권 문구는 투명 레이어인 `PSP_GAME/PIC0.PNG`이다.
- 게임 목록의 작은 대표 이미지는 `PSP_GAME/ICON0.PNG`이다.
- 따라서 XMB 화면을 한글화하려면 최소한 `PIC0.PNG`을 번역해야 하며, 배경 디자인도 변경하려면 `PIC1.PNG`을 함께 교체하면 된다.

## 확인된 자산

| ISO 경로 | 용도 | 규격 | 원본 크기 | LBA | SHA-256 |
|---|---|---:|---:|---:|---|
| `PSP_GAME/ICON0.PNG` | 게임 목록 아이콘 | 144×80 RGB | 27,073 | 422,784 | `95BA2C6F4E0C5C640E092CDC14C1EC598A686073980EF82808A3B27880DC3CC2` |
| `PSP_GAME/PIC0.PNG` | 설명·저작권 투명 레이어 | 310×180 RGBA | 56,082 | 422,800 | `31E69F974EE5517BCD541DC1305256C1379F53A19543C0353D740DC1800851A0` |
| `PSP_GAME/PIC1.PNG` | XMB 전체 배경 | 480×272 RGB | 288,562 | 422,832 | `92B05E2E8073CF6EDA70141FB4183DAA208D3D7E12D4147EAA672BBF3B6FC2DE` |
| `PSP_GAME/PARAM.SFO` | XMB 메타데이터 | 바이너리 | 472 | 422,768 | `48EA754BB2F4F3AC055B421BA3D08A0C5FB53BB2BB7E29D51C08CB51096F721E` |

- `PSP_GAME/SND0.AT3`은 이 ISO에 존재하지 않는다.

## 산출물

- 추출 도구: `tools/scripts/ys6_xmb_image_discovery.py`
- 원본 추출 경로: `tools/patchdata/work/current/097-psp-xmb-images`
- 추출 메타데이터: `tools/patchdata/work/current/097-psp-xmb-images/report.json`

## 패치 영향 확인

- 현재 `roms/Ys VI - Korean Patched.iso`에서 같은 자산을 다시 추출해 비교했다.
- `ICON0.PNG`, `PIC0.PNG`, `PIC1.PNG`, `PARAM.SFO`의 LBA, 크기와 SHA-256이 원본 ISO와 모두 일치했다.
- 즉, 현재 빌더는 XMB 자산을 변경하지 않으며 기존 패치 내용에도 영향을 주지 않는다.

## 교체 시 조건

- `PIC1.PNG`은 480×272 RGB, `PIC0.PNG`은 310×180 RGBA, `ICON0.PNG`은 144×80 RGB 규격을 유지하는 것이 안전하다.
- 현재 ISO의 고정 extent에서 교체하려면 PNG 파일 크기는 각각의 할당 공간 이하여야 한다.
  - `ICON0.PNG`: 28,672바이트 이하
  - `PIC0.PNG`: 57,344바이트 이하
  - `PIC1.PNG`: 288,768바이트 이하
- 실제 한글 이미지 제작과 GUI 패치 연동은 별도 계획에서 진행한다.

## 검증

- 원본 ISO는 읽기 전용으로 조사했으며 수정하지 않았다.
- 세 PNG의 시각적 내용을 직접 확인했다.
- 추출 스크립트 Python 문법 검사를 통과했다.
