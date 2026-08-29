# ADR-004: MVP 기본 STT 모델로 `whisper-1` 사용

- 상태: Accepted
- 결정일: 2026-08-29

## 문맥

자막 시스템은 텍스트만 필요한 것이 아니라 각 세그먼트의 시작·종료 시간이 필요하다. 따라서
STT 모델의 품질만큼 현재 API 응답 형식과 timestamp 지원 여부가 중요하다.

## 결정

MVP 기본값은 `OPENAI_STT_MODEL=whisper-1`로 둔다. Adapter는 `verbose_json`과 segment timestamp를
요청하고, 모델명은 환경변수로 교체할 수 있게 한다.

## 결정 근거

실제 연동 smoke test에서 당시 `gpt-transcribe` 요청은 이 파이프라인이 요구한 `verbose_json` 응답
형식과 호환되지 않는 provider 오류를 반환했다. 반면 `whisper-1`은 현재 구현이 필요한 timed
segment 응답으로 전체 흐름을 검증할 수 있었다.

## 고려한 대안

- `gpt-transcribe` 계열: 최신 품질과 전사 기능을 다시 검증할 수 있지만, 응답 형식 및 timestamp
  지원을 모델별로 확인해야 한다.
- 자체 Whisper 서버: 데이터 통제와 비용 예측에 유리하지만 GPU 운영 범위가 커진다.
- STT timestamp를 별도 forced alignment로 생성: 정밀도는 높일 수 있지만 파이프라인이 복잡해진다.

## 결과

현재 MVP는 자막 시간축을 안정적으로 확보할 수 있다. 모델을 바꿀 때는 단순히 환경변수만 바꾸지
말고, Adapter 테스트와 실제 smoke test로 응답 형식을 먼저 확인해야 한다.

## 구현 상태

`.env.example`, `backend/app/providers/openai_adapters.py`, `documents/06-openai-integration.md`에
반영되어 있다.
