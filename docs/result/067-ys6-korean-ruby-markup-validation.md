# 067. Ys VI 한글 번역 ruby 마크업 검증 제외 결과

## 결과

- 한글 번역에서 일본어 읽는 법용 `<ruby:...>`와 `<endruby>` 태그를 생략해도
  검증 오류가 발생하지 않도록 수정했다.
- `<color:...>`, `<color:>` 등 ruby 이외의 마크업과 게임 제어 토큰 검사는
  기존대로 유지했다.
- 개별 번역 레코드에 `allow_markup_change`를 추가하거나 번역문을 수정하지 않았다.

## 변경 내용

- `tools/scripts/ys6_translation_workspace.py`
  - ruby 태그를 식별하는 정규식을 추가했다.
  - 한글 번역에서 보존해야 하는 마크업만 반환하는 `required_markup` 함수를
    추가했다.
  - 일반 작업공간 검증과 초벌 번역 병합 검증이 같은 함수를 사용하도록 했다.
- `tools/scripts/tests/test_ys6_translation_workspace.py`
  - ruby 생략 허용 테스트
  - color 누락 거부 테스트
  - ruby 생략과 color 보존 조합 테스트
  - 초벌 번역 병합 ruby 생략 테스트를 추가했다.

## 검증

- 관련 번역·빌더 테스트 27개 통과.
- 전체 `dialogue-translations.json` 검증 결과:
  - `valid: true`
  - 레코드: 7,424개
  - override: 4,766개
  - 오류: 0개
- 기존 ruby 오류가 발생했던 다음 레코드가 별도 예외 없이 통과했다.
  - `s_06/s_0699/startbossbattle.xso.z`, string index 4
  - `s_06/s_0699/startbossbattle.xso.z`, string index 16
- GUI와 동일한 사용자용 빌더 사전 검증 성공:
  - `valid: true`
  - 옵션 메뉴 이미지 적용: 9개
  - 추가 이미지 적용: 39개, 10개 리소스
  - 추가 이미지 런타임 복사본: 41/41
  - 할당 공간 초과: 0개

## 알려진 사항

- 전체 작업공간에 번역문은 있지만 상태가 `untranslated`인 레코드 1개와 `draft`인
  레코드 1개가 있어 경고 2건이 남아 있다. 오류가 아니므로 사전 검증을 막지 않는다.
- `allow_markup_change`는 ruby 외 다른 마크업을 의도적으로 변경할 때 사용하는 기존
  예외 기능으로 유지했다.
- 번역 데이터, 이미지 파일 및 원본 ISO는 수정하지 않았다.
