# Ys VI 검수 인물명 14개 일괄 적용 계획

## 상태

- 계획 작성: 완료
- 사용자 확인: 완료
- 구현 및 ISO 적용: 완료
- 정적 검증: 완료
- 인게임 검증: 완료
- 결과 문서: `/docs/result/029-ys6-reviewed-cast-name-batch.md`

## 배경

028에서 사용자용 인물명 정본을 `/tools/config/cast-names.json`으로 배치하고 GUI가 자동으로 읽도록 했다. 사용자가 인물명을 일부 번역하고 적용할 14개 항목을 `reviewed`로 지정했다.

현재 통합 빌더는 `reviewed` 인물명만 선택해 대사 글리프 매핑을 확장하고, standalone `castinfo.dat`와 `init.bin` 내부 사본을 함께 수정할 수 있다.

## 적용 대상

다음 14개만 적용한다.

| identifier | 원문 | 번역 |
|---|---|---|
| `CAST_C220` | オルハ | 오르하 |
| `CAST_C240` | イーシャ | 이샤 |
| `CAST_C250` | オード族長 | 오드족장 |
| `CAST_C620` | ロロ | 로로 |
| `CAST_C630` | トクサ | 토쿠사 |
| `CAST_C650` | マーヴ | 마브 |
| `CAST_C670` | ソラ | 소라 |
| `CAST_C690` | ラーゴ | 라고 |
| `CAST_C700` | シルバ | 실바 |
| `CAST_C730` | カマラ | 카말라 |
| `CAST_C740` | 猫 | 고양이 |
| `CAST_C750` | ミハイル | 미하일 |
| `CAST_C760` | グエン | 구엔 |
| `CAST_C770` | ニース | 니스 |

번역이 입력되어 있어도 `untranslated`인 나머지 항목은 적용하지 않는다.

## 목표

1. 인물명 작업공간과 원본 `castinfo.dat`의 identifier·원문 SHA를 검증한다.
2. reviewed 인물명에 필요한 한글 글리프를 누적 매핑에 추가한다.
3. 14개 이름을 두 `castinfo.dat` 사본에 동일하게 적용한다.
4. 기존 대사 115개와 글리프 정렬 설정을 유지한다.
5. 새 누적 ISO를 `/patched/029-reviewed-cast-name-batch`에 생성한다.

## 원본 및 작업본 보호

- 원본 ISO는 읽기 전용으로 유지한다.
- 기존 026·027 ISO를 덮어쓰지 않는다.
- `/tools/config/cast-names.json`은 빌드 입력으로만 읽고 자동 수정하지 않는다.
- 작업 경로는 `/.work/ys6-reviewed-cast-name-batch`로 분리한다.
- 결과 ISO는 `/patched/029-reviewed-cast-name-batch/Ys VI - reviewed-cast-names-korean-build.iso`로 생성한다.

## 처리 절차

1. `/tools/config/cast-names.json` 전체 스키마 검증
2. reviewed 항목 14개 고정 및 보고서 생성
3. 대사 115개와 인물명 14개의 한글 문자로 매핑 확장
4. 기존 `gulim.ttc`, 12px, 좌측 inset 1 설정으로 EBOOT 글리프 생성
5. 원본 standalone과 `init.bin` 내부 `castinfo.dat` 동일성 확인
6. identifier별 원문과 32바이트 필드 SHA 확인
7. 14개 이름 필드 수정
8. 대사 XSO·아카이브·standalone·EBOOT와 함께 누적 ISO 생성
9. ISO 변경 범위와 산출물 검증

## 정적 검증

- 작업공간 reviewed 수가 정확히 14개
- reviewed 번역의 빈 문자열·NUL 없음
- 각 인코딩 결과 + NUL이 32바이트 이하
- identifier 14개 모두 원본에 하나씩만 존재
- 이름 필드 밖 `castinfo.dat` 변경 0건
- standalone과 `init.bin` 내부 수정 사본 동일
- `init.bin` 대상 엔트리 밖 변경 0건
- 대사 reviewed 115개 유지
- 모든 신규 글리프 생성 성공 및 좌측 정렬 설정 유지
- 아카이브 및 ISO 할당 초과 없음
- 허용 ISO extent 밖 변경 0건
- 원본 ISO SHA-256 유지
- Python 컴파일 및 자동 테스트 통과

## 인게임 확인

접근 가능성이 확인된 항목을 우선 점검한다.

1. `이샤`
2. `오르하`
3. `토쿠사`

확인 내용:

- 대화창 인물명 한글 출력
- 글자 잘림·깨짐·자간 이상 없음
- 대사 본문 정상
- 선택지와 이벤트 진행 정상

나머지 인물명은 해당 캐릭터 등장 시 순차적으로 확인하며, 미확인 상태를 결과 문서에 기록한다.

## 예상 산출물

- 작업 경로: `/.work/ys6-reviewed-cast-name-batch`
- 레코드별 보고서: `castinfo-report.csv`
- 매핑 및 글리프 보고서
- 빌드 manifest와 preflight 보고서
- 검증 ISO: `/patched/029-reviewed-cast-name-batch/Ys VI - reviewed-cast-names-korean-build.iso`
- 결과 문서: `/docs/result/029-ys6-reviewed-cast-name-batch.md`

## 완료 조건

- reviewed 14개만 이름 필드에 적용된다.
- 두 `castinfo.dat` 사본이 동일하다.
- 기존 누적 대사와 글리프 설정이 유지된다.
- 정적 검증과 자동 테스트가 통과한다.
- 사용자가 접근 가능한 대표 인물명을 PPSSPP에서 확인한다.
- 결과 문서에 확인·미확인 항목을 구분해 기록한다.

## 중단 및 재확인 조건

- reviewed 수나 번역 내용이 계획 작성 시점의 14개와 달라짐
- 원문 SHA 또는 identifier 불일치
- 한글 글리프 슬롯 부족
- 32바이트 이름 필드 초과
- 아카이브 또는 ISO 할당 초과
- 실행 코드 수정 필요
- 대상 이름 필드 밖 데이터 변경
- 기존 대사나 이벤트 회귀 발생
