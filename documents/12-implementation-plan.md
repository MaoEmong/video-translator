# 12. 구현 계획

현재까지 Phase 0과 Phase 1의 핵심 백엔드 흐름을 구현했다. 아래 목록에서 `[x]`는 코드와
테스트가 준비된 항목이고, `[ ]`는 후속 작업이다.

## Phase 0: 기반 구조

- [x] 프로젝트 디렉터리 구성
- [x] 환경변수와 설정 모듈
- [x] PostgreSQL migration
- [x] Object Storage 연결
- [x] 공통 ID와 오류 형식
- [x] 기본 로깅

## Phase 1: 기본 파이프라인

- [x] 업로드 세션 API
- [x] 영상 업로드 완료 및 상태 검증
- [x] FFmpeg 오디오 추출
- [x] Redis Queue와 Worker
- [x] OpenAI STT Adapter
- [x] Transcript 저장·정규화
- [x] OpenAI 번역 Adapter
- [x] SRT/VTT 생성

## Phase 2: 제품 기능

- [x] 작업 상태 UI
- [x] VTT 지원
- [x] 세그먼트 조회와 편집
- [x] 번역 버전 관리
- [x] 재번역
- [ ] 실패 단계 재시도 정책
- [x] 결과 다운로드 URL

## Phase 3: 운영 안정화

- 인증과 사용자별 권한
- 사용자별 quota
- 비용 추적
- 자동 파일 삭제
- 모니터링과 알림
- 백업과 복구 테스트
- 보안 점검

## Phase 4: 확장 기능

- 화자 분리
- 사용자 용어집
- ASS 스타일 자막
- 번역 영상 렌더링
- 음성 더빙
- 실시간 처리

## 첫 구현의 종료 조건

짧은 테스트 영상을 업로드한 뒤 다음이 자동으로 완료되어야 한다.

```text
영상 업로드
  → STT
  → 한국어 번역
  → SRT 생성
  → 결과 다운로드
```

이후 같은 Transcript로 일본어 번역 Job을 추가할 수 있어야 한다.
