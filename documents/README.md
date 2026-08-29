# 영상 번역 자막 시스템 설계 문서

이 폴더는 외국어 영상의 음성을 인식하고 번역 자막을 생성하는 시스템의 아키텍처와 세부 설계를
관리한다. 포트폴리오 리뷰에서는 표준 문서를 먼저 읽고, 주제별 문서에서 구현 세부사항을 확인한다.

## 표준 아키텍처 문서

- [arc42 전체 구조](./arc42/README.md): 목표, 제약, 컨텍스트, 런타임, 배포, 품질과 위험
- [C4 모델](./c4/README.md): System Context, Container, Component 다이어그램
- [ADR 결정 기록](./adr/README.md): 중요한 기술 선택의 배경과 결과

## 문서 목록

1. [전체 개요](./00-overview.md)
2. [시스템 아키텍처](./01-architecture.md)
3. [처리 파이프라인](./02-processing-pipeline.md)
4. [데이터 모델](./03-data-model.md)
5. [외부 API](./04-api.md)
6. [Queue와 Worker](./05-queue-workers.md)
7. [OpenAI 연동](./06-openai-integration.md)
8. [자막 생성 규칙](./07-subtitle-rules.md)
9. [보안과 개인정보](./08-security-privacy.md)
10. [관측성과 운영](./09-observability.md)
11. [배포와 인프라](./10-deployment.md)
12. [테스트 전략](./11-testing.md)
13. [구현 계획](./12-implementation-plan.md)
14. [운영 확장 검토 사항](./13-open-decisions.md)
15. [포트폴리오 범위](./14-portfolio-scope.md)

통합본은 루트의 [`DESIGN.md`](../DESIGN.md)에서 확인할 수 있다.

## 문서 작성 원칙

- 구현 결정은 관련 항목의 문서에 먼저 기록한다.
- API, DB, Queue 메시지의 이름은 문서 전체에서 동일하게 유지한다.
- 현재 MVP의 결정은 `adr/`에 기록하고, 아직 구현하지 않은 운영 확장 항목은 `13-open-decisions.md`에 기록한다.
- 실제 구현과 설계가 달라지면 해당 문서와 통합본을 함께 갱신한다.
