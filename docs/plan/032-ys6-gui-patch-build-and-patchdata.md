# Ys VI GUI 패치 빌드 탭 및 `/tools/patchdata` 전환 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- 패치 자산 이관: 완료
- GUI 빌드 탭: 완료
- 자동·재현 검증: 완료
- 사용자 GUI 빌드 확인: 완료
- 결과 문서: `/docs/result/032-ys6-gui-patch-build-and-patchdata.md`

## 목적

사용자가 GUI에서 원본 ISO를 선택하고 현재 승인된 대사·인물명으로 패치 ISO를 직접 생성할 수 있게 한다. 빌드에 필요한 정적 데이터와 실행 산출물은 더 이상 `/.work`를 참조하지 않고 `/tools/patchdata` 아래에서 관리한다.

## 디렉터리 구조

```text
tools/
  ys6_dialogue_viewer.py
  config/
    dialogue-translations.json
    cast-names.json
    dialogue-catalog.json
  patchdata/
    runtime-archive-map.json
    font-usage.json
    seed-mapping.json
    original-eboot.bin
    hangul-98fc-manual.txt
    standalone-paths.json
    build-config.json
    work/
      current/
  scripts/
```

정적 패치 자산은 `/tools/patchdata` 루트에 둔다. 매 빌드 보고서·재구축 XSO·EBOOT·아카이브 등은 `/tools/patchdata/work/current`에 생성한다.

## 이관 대상

- 런타임 XSO 대응표
  - `runtime_archive_xso_map.json` → `runtime-archive-map.json`
- 폰트 슬롯 사용 정보
  - `font-usage.json`
- 기존 한글 코드 매핑
  - `mapping.json` → `seed-mapping.json`
- 복호화된 원본 실행 파일
  - `ULJM05009_EBOOT.BIN` → `original-eboot.bin`
- 수동 `한` 글리프
  - `hangul-98fc-manual.txt`
- standalone XSO 38개 경로
  - 기존 CSV에서 `standalone-paths.json`으로 정리
- 빌드 기본 설정
  - 원본 ISO SHA-256
  - 원본 EBOOT SHA-256
  - 폰트 크기 12px
  - 좌측 inset 1
  - 기본 출력 파일명

각 파일에는 SHA-256을 계산하고 `build-config.json`에 기대 해시를 기록한다. 원본 `/.work` 자료는 삭제하지 않는다.

## 폰트 처리

현재 빌드는 Windows의 `C:/Windows/Fonts/gulim.ttc`를 사용한다. 시스템 폰트 파일 자체는 `/tools/patchdata`에 복사하지 않는다.

- 기본 경로에서 굴림 폰트를 자동 탐색
- 찾지 못하면 GUI에서 TTC/TTF 파일 선택
- 선택 경로는 GUI 세션 설정으로 사용
- 폰트가 없으면 빌드를 시작하지 않고 명확히 안내

## 비GUI 빌드 래퍼

`/tools/scripts`에 사용자 빌드용 Python 래퍼를 추가한다.

역할:

- `/tools/config` 및 `/tools/patchdata` 기본 경로 해석
- 정적 자산 존재 여부와 SHA 검증
- 대사 `override` 및 인물명 `reviewed` 수 산출
- standalone 경로 자동 전달
- preflight와 build 공통 실행
- 진행 이벤트 또는 단계별 콜백 제공
- 기존 `ys6_integrated_build.py` 로직 재사용

GUI가 긴 명령행을 직접 조립하지 않게 한다. 비GUI에서도 같은 래퍼를 실행할 수 있게 한다.

## GUI `패치 빌드` 탭

기존 Notebook에 세 번째 탭을 추가한다.

### 입력

- 원본 ISO 경로 및 찾아보기
- 출력 ISO 경로 및 찾아보기
- 폰트 경로 및 찾아보기
- 현재 대사 override 수
- 현재 대사 draft 수
- 현재 인물명 reviewed 수

### 작업 버튼

- `데이터 다시 읽기`
- `사전 검증`
- `패치 ISO 만들기`
- `작업 폴더 열기`는 플랫폼/권한 문제가 있으므로 필수 범위에서 제외하고 결과 경로만 표시

### 진행 표시

- 작업 단계 텍스트
- 진행 중 버튼 비활성화
- 진행 표시줄
- 로그 창
- 완료 시 출력 ISO SHA-256 표시

빌드는 GUI 응답이 멈추지 않도록 백그라운드 스레드에서 실행하고, Tk 위젯 갱신은 메인 스레드 큐를 통해 처리한다.

## 빌드 동작

1. GUI의 미저장 대사·인물명 변경이 있으면 저장 안내
2. 원본 ISO SHA-256 검증
3. `/tools/patchdata` 정적 자산 SHA 검증
4. 대사 작업공간 검증
5. 대사 `override`만 선택
6. 인물명 `reviewed`만 선택
7. preflight 수행
8. 사용자가 빌드를 실행하면 별도 출력 ISO 생성
9. manifest와 보고서를 `/tools/patchdata/work/current`에 기록
10. 결과 SHA와 경로 표시

`draft`는 번역문이 있어도 빌드 대상에서 제외한다.

## 작업 폴더 관리

- 매번 새 ROM을 만들지 않도록 사용자가 지정한 출력 ISO 하나를 사용한다.
- 기존 출력 파일이 있으면 임의 덮어쓰기하지 않고 GUI에서 명확히 확인받는다.
- `/tools/patchdata/work/current`는 직전 빌드 보고용으로 재사용한다.
- 재사용 전에 정확한 대상 경로를 검증한다.
- 삭제 대신 새 실행이 필요한 파일을 덮어쓰는 방식은 각 빌드 도구의 `overwrite` 옵션과 원자적 출력 규칙을 따른다.
- 실패 시 원본 ISO와 기존 완성 ISO는 보존한다.

## 검증

### 자산 이관

- 원본 `.work` 파일과 이관 사본 SHA 일치
- standalone 경로 38개 유지
- 모든 경로가 `.work` 없이 해석됨
- 패치 데이터 누락·해시 변경 역테스트

### GUI

- 원본 ISO 선택
- 출력 경로 선택
- 상태 수 표시
- preflight 실행 중 UI 응답 유지
- 성공·실패 로그 표시
- 잘못된 ISO 차단
- 출력 파일 충돌 확인
- 직접 실행 및 패키지 import 통과

### 빌드

- `/tools/patchdata`만 사용한 CLI preflight 통과
- GUI와 CLI 래퍼가 동일 입력으로 동일 ISO 생성
- 현재 031 작업공간 기준 재빌드 SHA가 031 ISO와 동일
- override 142개 적용
- draft 19개 제외
- 인물명 14개 적용
- 허용 ISO 범위 밖 변경 0건
- 원본 ISO 보존
- 자동 테스트 및 Python 컴파일 통과

## 보안 및 배포 참고

`original-eboot.bin`, 런타임 맵, 카탈로그 및 기타 게임 유래 데이터는 원본 게임에서 추출된 자료일 수 있다. 저장소 내부 개발에는 사용하되, 제3자 배포 패키지에 포함할 수 있는지는 별도 검토가 필요하다. 이번 작업은 현재 로컬 저장소에서 GUI 빌드를 가능하게 하는 범위다.

## 예상 변경 파일

- 생성: `/tools/patchdata/*`
- 생성: `/tools/scripts/ys6_patch_builder.py`
- 수정: `/tools/ys6_dialogue_viewer.py`
- 수정: `/tools/scripts/ys6_integrated_build.py` 또는 호출 인터페이스
- 추가·수정: `/tools/scripts/tests`
- 결과 문서: `/docs/result/032-ys6-gui-patch-build-and-patchdata.md`

## 완료 조건

- GUI에서 원본 ISO를 선택해 패치 ISO를 생성할 수 있다.
- GUI 및 빌더가 `.work`의 정적 입력을 참조하지 않는다.
- 정적 자산과 작업 산출물이 `/tools/patchdata`에서 관리된다.
- override/draft 적용 규칙이 유지된다.
- 031과 동일 입력으로 바이트 동일 ISO를 재현한다.
- 사용자 GUI 빌드 확인 후 결과 문서를 작성한다.

## 중단 및 재확인 조건

- `.work` 이관 사본의 SHA 불일치
- 게임 유래 자산의 저장소 포함 범위를 변경해야 함
- GUI 스레드에서 파일 손상 또는 UI 정지 발생
- 031 ISO를 바이트 단위로 재현하지 못함
- 출력 ISO가 원본 또는 기존 패치 ISO와 같은 경로로 지정됨
- 허용 extent 밖 변경 또는 아카이브 용량 초과
