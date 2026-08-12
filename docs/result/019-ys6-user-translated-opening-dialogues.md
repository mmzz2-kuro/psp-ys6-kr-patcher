# 019 사용자 번역 오프닝 대사 적용 결과

## 결과

`s_0551`의 대사 인덱스 35~43에 사용자가 작성한 한국어 번역 9개를 적용했다. 필요한 한글 글리프를 복호화 EBOOT에 추가하고, 가변 길이 XSO 재조립·압축·런타임 아카이브 교체를 거쳐 ISO 단독 실행이 가능한 작업본을 생성했다.

PPSSPP에서 한글 대사, 줄바꿈, 문장부호 및 이벤트 진행을 확인했다. 최초 확인에서 말줄임표가 앞 한글과 붙어 보이는 문제가 발견돼 한글 뒤 말줄임표 앞에 좁은 ASCII 공백을 넣는 빌드 보정을 추가했다. 재보정본은 사용자의 인게임 확인에서 정상 출력됐다.

## 적용 내용

- 대상 맵: `s_0551`
- 대상 XSO: `s_0551.xso.z`
- 대사 인덱스: 35~43
- 적용 대사 수: 9개
- 한글 매핑 수: 기존 10자를 포함해 총 58자
- 폰트: Gulim Regular 기반 16×12, 1bpp 글리프
- 안전 가시 폭: 12픽셀
- 런타임 아카이브: `PSP_GAME/USRDIR/data/arc/s_0551.bin`

문장부호는 빌드 단계에서 다음과 같이 정규화한다.

- `,`, `?`, `!`는 CP932 전각 문장부호로 변환
- 연속된 `..`, `...`는 게임의 `……`로 변환
- 한글 바로 뒤에서 시작하는 `……` 앞에는 ASCII 공백 1바이트 삽입
- 문장 시작과 줄바꿈 직후의 `……`에는 앞 공백을 삽입하지 않음
- 사용자가 작성한 번역 정본은 변경하지 않음

## 생성 및 변경 파일

- 최종 ISO: `/patched/019-user-opening-translation/Ys VI - user-opening-translation.iso`
- 계획 문서: `/docs/plan/019-ys6-user-translated-opening-dialogues.md`
- 한글 인코딩 및 문장부호 보정: `/tools/scripts/ys6_hangul_codec.py`
- 번역 일괄 빌드: `/tools/scripts/ys6_translation_build.py`
- 번역 작업공간 준비: `/tools/scripts/ys6_translation_workspace.py`
- 테스트: `/tools/scripts/tests/test_ys6_hangul_pipeline.py`
- 작업 산출물: `/.work/ys6-user-opening-translation`

## 정적 검증

| 항목 | 결과 |
|---|---|
| 원본 ISO SHA-256 | `0133DC75EEEFB7E1864180C88E486D2EEBE9AE3D1DBFA990BEF57E28BAAE082B` |
| 최종 ISO SHA-256 | `0F33526C62BD04DC56390D900CEAE9312AC4AFB4F4FFA29F9A78D81D9E127AD7` |
| ISO 내부 EBOOT SHA-256 | `E302ABAC588FFDC65C6A885D68B51E160ECC6F140F4CFA0D33DFF95FC2F34A87` |
| 최종 `s_0551.bin` SHA-256 | `C7178340479A1791419F5F2B50B5F3993BADE77486628FB53F9C1100D469F922` |
| 재조립 XSO 크기 | 4,495바이트 |
| 재조립 XSO SHA-256 | `5799FD427D21DDB821F97E7A80B185BB2A45B36C7CDABE795C480A7E521EDBB4` |
| 압축 `.xso.z` 크기 | 1,964바이트 |
| 압축 `.xso.z` SHA-256 | `ED4CC217BF195D6CC14B45EA35E3B4D927DCE0E1781464C9FA03F25A24DE6456` |
| 기존 할당 공간 | 2,048바이트 |
| 남은 공간 | 84바이트 |
| 허용 범위 밖 ISO 변경 | 0건 |
| 자동 테스트 | 54건 통과 |
| Python 바이트코드 컴파일 | 통과 |

최종 ISO에서 다시 읽은 EBOOT와 `s_0551.bin`의 크기·SHA-256이 준비한 교체 파일과 일치했다. 두 파일의 extent는 원본과 동일하며 ISO 크기도 증가하지 않았다.

## 인게임 검증

- PPSSPP 완전 종료 후 재실행
- 새 게임에서 대사 인덱스 35~43 확인
- 한글 글리프 출력 정상
- 줄바꿈 포함 대사 출력 정상
- 쉼표·물음표·느낌표 출력 정상
- 말줄임표 좌측 간격 재보정 후 출력 정상
- 두 번째 대사와 뒤쪽 대사 정상 출력
- 이벤트 정상 진행

사용자 확인 결과 현재 발견된 문제는 없다.

## 알려진 사항

말줄임표 간격은 게임 렌더러나 폰트 테이블을 수정한 것이 아니라 빌드 시 문맥에 따라 ASCII 공백을 삽입하는 방식이다. 이후 다른 대사나 UI에서 간격이 과도하거나 부족한 사례가 발견되면 현재 결과를 유지한 채 별도 계획으로 다음 대안을 검토한다.

- 말줄임표 글리프 자체의 좌측 여백 조정
- 문맥별 간격 규칙 세분화
- 대사와 UI 문자열의 정규화 정책 분리

## 정리

최종 ISO 한 개만 `/patched/019-user-opening-translation`에 유지했다. 생성 과정의 중간 ISO는 삭제했으며 원본 ISO는 수정하지 않았다. `/.work/ys6-user-opening-translation`의 XSO·압축 파일·매핑·보고서는 재현과 후속 문제 분석을 위해 유지한다.
