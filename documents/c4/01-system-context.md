# C4 Level 1: System Context

## 다이어그램

```mermaid
flowchart LR
    USER[Person<br/>사용자] -->|영상 업로드, 번역 요청, 자막 편집 및 다운로드| SYSTEM[System<br/>Video Translator MVP]
    SYSTEM -->|음성 인식과 번역 요청| OPENAI[External System<br/>OpenAI Platform]
    SYSTEM -->|원본 영상과 자막 저장/조회| STORAGE[External System<br/>Private Object Storage]
    SYSTEM -->|상태와 작업 정보 저장| DATA[Supporting Systems<br/>PostgreSQL 및 Redis]
```

## 관계

| 요소 | 설명 |
|---|---|
| 사용자 | 외국어 영상의 목표 언어를 선택하고 결과 자막을 검토한다. |
| Video Translator MVP | 업로드, 비동기 처리, AI 호출, 자막 편집과 export를 조정한다. |
| OpenAI Platform | timed STT와 구조화된 번역 결과를 제공한다. |
| Private Object Storage | 원본 영상, 정규화 오디오, 결과 자막을 보관한다. |
| PostgreSQL 및 Redis | 작업 상태와 도메인 데이터를 저장하고 비동기 메시지를 전달한다. |
