# arc42 아키텍처 문서

이 디렉터리는 프로젝트 아키텍처를 arc42의 12개 섹션으로 정리한 포트폴리오용 기준 문서다.
현재 구현된 MVP와 운영 서비스로 확장할 때 필요한 차이를 함께 표시한다.

## 섹션

1. [소개와 목표](./01-introduction-and-goals.md)
2. [제약사항](./02-constraints.md)
3. [시스템 범위와 컨텍스트](./03-context-and-scope.md)
4. [해결 전략](./04-solution-strategy.md)
5. [구성 블록 뷰](./05-building-block-view.md)
6. [런타임 뷰](./06-runtime-view.md)
7. [배포 뷰](./07-deployment-view.md)
8. [횡단 관심사](./08-cross-cutting-concepts.md)
9. [아키텍처 결정](./09-architecture-decisions.md)
10. [품질 요구사항](./10-quality-requirements.md)
11. [위험과 기술 부채](./11-risks-and-technical-debt.md)
12. [용어집](./12-glossary.md)

## 관련 표준 문서

- [C4 모델](../c4/README.md): 구조를 시각적으로 설명한다.
- [ADR](../adr/README.md): 중요한 선택의 배경과 결과를 기록한다.
- [주제별 상세 설계](../README.md): API, 데이터 모델, 테스트 등 구현 세부사항이다.

## 읽는 순서

면접이나 코드 리뷰에서는 01 → 03 → 04 → 05 → 06 순서로 읽으면 전체 흐름을 빠르게 파악할 수
있다. 구현 근거가 필요하면 각 섹션에서 연결한 주제별 상세 문서와 실제 코드로 내려간다.
