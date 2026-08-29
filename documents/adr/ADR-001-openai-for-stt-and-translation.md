# ADR-001: STT와 번역 provider로 OpenAI 사용

- 상태: Accepted
- 결정일: 2026-08-29

## 문맥

서비스의 핵심은 영상 음성을 원문 자막으로 만들고 이를 목표 언어로 번역하는 것이다. 포트폴리오
MVP에서 여러 AI provider를 동시에 운영하면 인프라와 테스트 코드가 분산된다.

## 결정

STT와 번역 LLM은 OpenAI API를 사용한다. 애플리케이션은 `OpenAISttAdapter`와
`OpenAITranslationAdapter`를 통해서만 provider를 호출한다.

- STT 응답은 timed segment로 변환한다.
- 번역 요청은 segment ID를 포함한 구조화 JSON으로 보낸다.
- Adapter에서 timeout, provider 오류, 응답 검증, 사용량 기록을 담당한다.
- 모델명은 환경변수로 설정한다.

## 고려한 대안

- 로컬 Whisper 및 로컬 번역 모델: 비용과 데이터 통제에는 유리하지만 MVP 환경 구성과 성능 검증
  부담이 크다.
- 여러 provider 추상화부터 구현: 확장성은 높지만 현재 데모의 핵심 흐름보다 추상화 코드가 커진다.
- API route에서 직접 호출: 구현은 빠르지만 외부 API 변화와 오류 처리가 도메인 로직에 섞인다.

## 결과

OpenAI 호출을 교체 가능한 경계로 만들면서도 MVP의 구현과 시연을 단순하게 유지한다. 대신 외부
네트워크와 모델별 응답 차이에 영향을 받으므로 실제 smoke test와 provider contract test가 필요하다.

## 구현 상태

`backend/app/providers/openai_adapters.py`와 Worker pipeline에 반영되어 있다.
