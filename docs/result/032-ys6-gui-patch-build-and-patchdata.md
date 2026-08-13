# Ys VI GUI 패치 빌드 탭 및 `/tools/patchdata` 전환 결과

## 상태

- 작업 번호: 032
- 패치 자산 이관: 완료
- GUI 패치 빌드 탭: 완료
- 자동 및 재현 검증: 완료
- 사용자 GUI 실행 및 ISO 빌드 확인: 완료
- 작업일: 2026-08-13

## 결과 요약

빌드에 필요한 정적 입력을 `/.work`에서 `/tools/patchdata`로 이관하고, 기존 GUI에 `패치 빌드` 탭을 추가했다. 사용자는 원본 ISO와 출력 경로를 선택한 후 사전 검증 또는 패치 ISO 생성을 직접 실행할 수 있다.

GUI와 비GUI 빌드는 동일한 `/tools/scripts/ys6_patch_builder.py` 래퍼를 사용한다. 래퍼는 긴 통합 빌드 인자를 캡슐화하고 `/tools/config`와 `/tools/patchdata`를 실행 위치와 무관하게 찾는다.

## `/tools/patchdata` 구성

- `runtime-archive-map.json`
- `font-usage.json`
- `seed-mapping.json`
- `original-eboot.bin`
- `hangul-98fc-manual.txt`
- `standalone-paths.json` — 38개
- `build-config.json` — 원본 해시, 글리프 설정, 자산 해시
- `work/current/` — 직전 빌드 보고서와 중간 산출물

정적 자산은 이관 원본과 SHA-256이 동일하다. `build-config.json`의 기대 해시와 다르면 빌드 전에 중단한다.

시스템 굴림 글꼴은 복사하지 않는다. `C:/Windows/Fonts/gulim.ttc`를 자동 탐색하며 없으면 GUI에서 TTC/TTF를 직접 선택할 수 있다.

## GUI 패치 빌드 탭

지원 기능:

- 원본 ISO 찾아보기
- 출력 ISO 찾아보기
- 글꼴 자동 탐색 및 찾아보기
- 대사 override·draft 및 인물명 reviewed 수 표시
- 패치 데이터 다시 읽기
- 사전 검증
- 패치 ISO 생성
- 기존 출력 파일 덮어쓰기 확인
- 실행 로그, 결과 경로 및 SHA-256 표시
- 빌드 중 버튼 비활성화와 진행 표시
- 백그라운드 스레드 실행으로 UI 응답 유지
- 미저장 대사·인물명 발견 시 저장 확인

원본과 출력 ISO가 같은 경로이면 중단하고, 지원하는 원본 SHA가 아니어도 중단한다.

## 현재 데이터

- 전체 대사: 7,424개
- override: 142개
- draft: 19개 — 빌드 제외
- 인물명 reviewed: 14개
- 글리프: 257개

## 검증 결과

- `/tools/patchdata`만 사용하는 inspect 통과
- `/tools/patchdata`만 사용하는 preflight 통과
- `.work` 정적 입력을 전달하지 않은 build 통과
- 자동 테스트 93개 통과
- Python 컴파일 통과
- 패키지 import 통과
- 파일 경로 직접 실행 import 통과
- 아카이브 할당 초과 0건
- 허용 ISO 범위 밖 변경 0건

재현 검증 ISO:

- `/patched/032-gui-patch-build/Ys VI - GUI patchdata verification.iso`
- SHA-256: `754DE4463A7902588C2F028E63B0383BBC1503DFB65B719E25316D835893CE08`

기존 031 인게임 검증 ISO와 바이트 단위로 완전히 동일하다. 원본 ISO SHA-256도 유지됐다.

## 사용 방법

1. `python tools/ys6_dialogue_viewer.py` 실행
2. `패치 빌드` 탭 선택
3. 원본 일본어 ISO 선택
4. 출력 ISO 경로 선택
5. 표시된 override/draft/reviewed 수 확인
6. `사전 검증` 실행
7. 성공하면 `패치 ISO 만들기` 실행
8. 로그 하단의 결과 SHA-256 확인

## 변경 파일

- 생성: `/tools/patchdata/*`
- 생성: `/tools/scripts/ys6_patch_builder.py`
- 생성: `/tools/scripts/tests/test_ys6_patch_builder.py`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정: `/tools/scripts/ys6_font_patch.py`
- 생성: `/patched/032-gui-patch-build/Ys VI - GUI patchdata verification.iso`

## 참고

`original-eboot.bin` 등 게임 유래 정적 데이터의 외부 배포 가능 여부는 별도 검토가 필요하다. 현재 구현은 로컬 저장소에서 사용자가 패치 ISO를 직접 생성하는 범위다.

## 후속 import 수정

GUI를 `python tools/ys6_dialogue_viewer.py`로 직접 실행할 때 `/tools/scripts`가 모듈 검색 경로에 없어 패치 빌더를 불러오지 못하는 문제를 수정했다.

- GUI 파일 위치를 기준으로 `/tools/scripts`를 명시적으로 모듈 경로에 추가
- 패치 빌더와 통합 빌더에 패키지 상대 import 지원 추가
- 폰트 빌드 모듈의 패키지 상대 import 지원 추가
- 저장소 루트를 제거한 격리된 직접 실행 조건에서 import 및 `inspect_inputs()` 성공
- 저장소 루트 패키지 import 성공
- 전체 자동 테스트 93개 통과

사용자가 수정 후 GUI가 정상 실행되고 `패치 빌드` 탭에서 ISO 빌드도 완료되는 것을 확인했다.
