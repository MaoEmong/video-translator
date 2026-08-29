# C4 모델

C4는 시스템을 사용자와 외부 시스템, 실행 단위, 주요 컴포넌트 수준으로 나눠 설명한다. 이
프로젝트에서는 arc42의 3~7번 섹션을 보완하는 시각 문서로 사용한다.

## 뷰

1. [System Context](./01-system-context.md): 사용자가 시스템과 어떤 외부 서비스에 의존하는지
2. [Container](./02-container.md): Web UI, API, Worker, 저장소의 실행 단위와 연결
3. [Component](./03-component.md): API와 Worker 내부의 주요 책임 분리

다이어그램은 현재 MVP 구현을 기준으로 하며, 아직 구현하지 않은 운영 서비스는 별도로 표시하지
않는다.
