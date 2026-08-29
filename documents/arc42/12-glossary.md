# 12. 용어집

| 용어 | 의미 |
|---|---|
| Video | 사용자가 업로드한 원본 영상의 메타데이터와 Storage 위치 |
| Media Asset | 원본 영상, 정규화 오디오 등 파생 파일 |
| Transcript | STT 결과와 원문 세그먼트의 묶음 |
| Transcript Segment | 시작/종료 시간과 원문을 가진 자막 단위 |
| Translation Job | 특정 Transcript를 목표 언어로 번역하는 비동기 작업 |
| Translation Version | 하나의 Job에서 생성된 번역 결과 버전 |
| Translation Segment | 원문 세그먼트에 대응하는 번역문과 편집 시간 |
| Job Step | validate, extract audio, transcribe, translate, build subtitle 같은 처리 단계 |
| Artifact | Storage에 저장된 SRT/VTT 결과 파일 |
| Signed URL | private Storage 객체에 제한된 시간 동안 접근할 수 있는 URL |
| Provider Adapter | 외부 OpenAI 요청, 응답 검증, 오류 변환을 감싸는 계층 |
