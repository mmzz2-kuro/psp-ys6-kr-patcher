# 067. Ys VI 한글 번역 ruby 마크업 검증 제외 계획

상태: 완료

## 배경

- 현재 번역 검증기는 원문과 번역문의 모든 `<...>` 마크업 목록이 같아야 한다.
- 일본어 읽는 법을 표시하는 `<ruby:...>...<endruby>`는 한글 번역에 필요하지
  않지만, 번역문에서 제거하면 `markup mismatch` 오류가 발생한다.
- 현재 실제 오류는 `s_06/s_0699/startbossbattle.xso.z`의 string index 4와
  16에서 확인됐다.

## 변경 계획

1. 마크업 비교 전에 ruby 전용 태그를 제외하는 공통 함수를 추가한다.
   - `<ruby:...>`
   - `<endruby>`
2. `<color:...>`, `<color:>` 등 나머지 마크업은 기존처럼 원문과 번역문이
   일치해야 한다.
3. 일반 작업공간 검증과 초벌 번역 병합 검증에 같은 정책을 적용한다.
4. 기존 `allow_markup_change`는 ruby 외 다른 마크업을 의도적으로 바꾸는 예외
   기능으로 유지한다.
5. 개별 번역 레코드에 `allow_markup_change`를 추가하지 않는다.

## 테스트 계획

1. 원문의 ruby 태그를 한글 번역에서 제거해도 검증이 통과하는지 확인한다.
2. `<color>` 태그가 누락되거나 값이 달라지면 계속 실패하는지 확인한다.
3. ruby와 color가 함께 있는 문장에서 ruby만 제거한 번역은 통과하는지 확인한다.
4. 초벌 번역 병합 경로도 같은 정책으로 동작하는지 확인한다.
5. 현재 전체 번역 작업공간을 다시 검증해 record 2776·2788 오류가 사라지는지
   확인한다.
6. GUI 사용자용 빌더 `inspect` 및 사전 검증을 다시 실행한다.

## 변경 대상

- `tools/scripts/ys6_translation_workspace.py`
- `tools/scripts/tests/test_ys6_translation_workspace.py`
- 필요 시 관련 초벌 번역 테스트
- `docs/result/067-ys6-korean-ruby-markup-validation.md`

## 완료 기준

- 한글 번역에서 ruby 태그 생략이 별도 레코드 예외 없이 허용된다.
- ruby 이외의 마크업과 제어 토큰 검사는 유지된다.
- 현재 전체 번역 작업공간과 GUI 사전 검증이 해당 오류 없이 통과한다.
- 번역 문자열과 원본 ISO는 수정하지 않는다.
