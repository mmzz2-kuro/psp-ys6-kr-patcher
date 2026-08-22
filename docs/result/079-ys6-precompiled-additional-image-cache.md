# 079. Ys VI 추가 이미지 사전 컴파일 캐시 최적화 결과

## 수행 내용

- 추가 이미지 리소스를 GUI 빌드 때마다 DXT1/DXT3로 재인코딩하던 경로에 사전 컴파일 캐시를 추가했다.
- 타블라스 14개를 포함해 현재 수정본이 존재하는 추가 이미지 리소스 27개를 모두 사전 컴파일했다.
- 캐시마다 원본 컨테이너, 리소스 정의, 적용 PNG 및 결과 컨테이너의 SHA-256을 기록했다.
- GUI 사전검증과 ISO 빌드는 모든 입력 해시가 일치할 때만 캐시 컨테이너를 사용한다.
- PNG 또는 매니페스트가 변경된 경우 오래된 캐시를 거부하고 재생성을 요구한다.
- `추가 이미지 적용` 체크박스를 해제하면 기존처럼 추가 이미지 캐시 검사와 적용을 모두 생략한다.

## 캐시 구조

- 경로: `tools/patchdata/ys6_additional_images/precompiled/`
- 컨테이너: 리소스별 `.dds.z` 27개
- 메타데이터: `precompiled/manifest.json`
- 전체 캐시 컨테이너 크기: 799,240바이트

메타데이터에는 다음 항목이 포함된다.

- 리소스 ID와 ISO 경로
- 원본 `.dds.z` SHA-256
- 매니페스트 리소스 정의 SHA-256
- 적용 PNG 목록과 각 SHA-256
- 패치 컨테이너 및 payload SHA-256
- 컨테이너 크기, 할당 공간과 잔여 공간
- 변경 DXT 블록 수와 세부 빌드 보고서

## 변경·생성 파일

- 변경: `tools/scripts/ys6_additional_image_patch.py`
- 변경: `tools/scripts/ys6_integrated_build.py`
- 추가: `tools/scripts/ys6_additional_image_precompile.py`
- 생성: `tools/patchdata/ys6_additional_images/precompiled/manifest.json`
- 생성: `tools/patchdata/ys6_additional_images/precompiled/*.dds.z` 27개

## 검증 결과

- Python 구문 검사: 성공
- 사전 컴파일 리소스: 27개
- GUI 공통 빌더 사전검증: 성공
- GUI 공통 빌더 ISO 생성: 성공
- 실제 빌드에서 캐시 사용: 27/27개
- 추가 이미지 런타임 복제본: 49/49 교체 성공
- 할당 공간 초과: 없음
- 현재 입력과 캐시 신원 해시 일치: 성공
- PNG 해시 변경 모의 시험에서 캐시 거부: 성공
- 최적화 전 078 ISO와 최적화 후 079 ISO SHA-256 일치: 성공

## 성능 비교

| 구분 | 최적화 전 관측 | 최적화 후 측정 |
|---|---:|---:|
| 전체 사전검증 | 약 7분 | 60.874초 |
| 전체 ISO 빌드 | 약 7분 | 87.593초 |

최적화 후 남은 시간은 대사 5,267개, XSO 563개, 아카이브 78개, 폰트 및 ISO 기록에 필요한 공통 처리 시간이다. 추가 이미지 DXT 재인코딩은 생략된다.

## 결과 동일성

- 078 ISO SHA-256: `ED79D5E88E2373050E248142DDDF97375081ADC0E5468CE45F020FA002B853BC`
- 079 ISO SHA-256: `ED79D5E88E2373050E248142DDDF97375081ADC0E5468CE45F020FA002B853BC`

두 ISO가 바이트 단위로 동일하므로 캐시 사용으로 이미지 품질이나 패치 내용은 변경되지 않았다.

## 테스트 ISO

- 경로: `patched/079-ys6-precompiled-additional-image-cache/Ys VI (Japan) - 079-precompiled-cache-test.iso`
- 용도: 캐시 빌드 결과와 078 결과의 동일성 및 소요 시간 검증
- 078 ISO와 완전히 동일하므로 둘 중 하나는 불필요한 중복 테스트 ROM이다.

## 캐시 갱신 방법

추가 이미지 PNG 또는 매니페스트를 변경한 뒤 다음 명령으로 캐시를 다시 생성한다.

```powershell
python tools/scripts/ys6_additional_image_precompile.py --iso "roms/Ys VI - Napishtim no Hako (Japan).iso"
```

GUI는 오래된 캐시를 임의로 사용하지 않고 `additional image precompiled cache is stale` 오류로 중단한다.
