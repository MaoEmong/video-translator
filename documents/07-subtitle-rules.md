# 07. 자막 생성 규칙

## 지원 형식

MVP:

- SRT
- VTT

후속:

- ASS
- 자막 번인 MP4

## 시간 규칙

- 내부 저장 단위는 밀리초 정수다.
- 기본 표시 시간은 원문 세그먼트의 `start_ms`, `end_ms`다.
- 사용자 수정값인 `display_start_ms`, `display_end_ms`가 있으면 이를 우선한다.
- `end_ms`는 `start_ms`보다 커야 한다.
- 음수 시간은 허용하지 않는다.
- 인접 자막의 과도한 겹침을 오류 또는 경고로 분류한다.

## 텍스트 규칙

- 최대 줄 수는 작업 설정으로 관리한다.
- 한 줄 최대 글자 수는 언어별 설정을 적용할 수 있다.
- 빈 번역문은 결과에 포함하지 않는다.
- 불필요한 양끝 공백을 제거한다.
- 자막 포맷별 특수문자를 escape한다.

## 품질 검사

```text
EMPTY_TEXT
INVALID_TIME_RANGE
OVERLAPPING_SEGMENTS
EXCESSIVE_LINE_LENGTH
EXCESSIVE_DURATION
MISSING_TRANSLATION
SEQUENCE_GAP
```

검사 결과는 오류와 경고로 나눈다. 오류가 있으면 artifact를 `FAILED`로 만들고, 경고만 있으면 사용자가 확인할 수 있도록 표시한다.

## 버전 처리

자막 artifact는 특정 `translation_version_id`를 참조한다. 사용자가 번역문을 수정한 뒤에는 새로운 artifact를 생성하고 기존 파일은 보존한다.
