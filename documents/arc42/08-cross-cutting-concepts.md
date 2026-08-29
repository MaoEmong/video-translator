# 8. 횡단 관심사

## 상태와 식별자

- 모든 주요 리소스는 UUID를 사용한다.
- Job과 Job Step의 상태는 DB에 저장하고 API polling이 이를 읽는다.
- Queue 메시지는 `job_id`, `step`, 관련 transcript/version 식별자를 포함한다.

## 오류 처리

- provider 오류는 timeout, rate limit, 인증, 잘못된 요청, 연결 실패 등 내부 코드로 변환한다.
- 단계 실패 시 `job_steps`에 오류를 남겨 어느 단계에서 실패했는지 확인한다.
- 번역 응답은 요청한 `segment_id`와 일치하는지 검증한다.

## 데이터 보안

- OpenAI API Key는 서버에서만 사용한다.
- Object Storage bucket은 private으로 운영한다.
- 파일명 대신 서버 생성 Storage key를 사용한다.
- 브라우저에는 만료되는 signed URL만 전달한다.

## 관측성

현재 MVP는 job, step, provider request ID와 사용량을 저장할 수 있는 모델을 갖는다. 운영 확장 시
구조화된 로그, metrics, trace와 알림을 붙인다. 세부 내용은 [관측성과 운영](../09-observability.md)을
참조한다.

## 테스트

provider와 Storage/Queue 경계에는 의존성 주입을 사용해 mock 테스트를 수행한다. 실제 환경에서는
Docker, FFmpeg, MinIO, OpenAI를 연결한 smoke test로 전체 흐름을 확인한다.
