# 🐶 Hackathon Test Project

Spring Boot(백엔드) + FastAPI(이미지/챗봇 AI) + Nginx(정적/리버스 프록시) + Bootstrap UI를 Docker Compose로 한 번에 실행합니다.

📖 위키(전체 문서): https://github.com/dorae222/hackathon_test/wiki

---

## 사전 준비(운영체제별 Docker 설치)

- Windows (PowerShell)
    - 설치: https://docs.docker.com/desktop/setup/install/windows-install/
    - 설치 후 Docker Desktop 실행 → 버전 확인
        ```powershell
        docker --version
        docker compose version
        ```

- macOS (zsh)
    - 설치: https://docs.docker.com/desktop/setup/install/mac-install/
    - 버전 확인
        ```bash
        docker --version
        docker compose version
        ```

- Linux (Ubuntu 등)
    - 설치 가이드: https://docs.docker.com/engine/install/
    - 버전 확인
        ```bash
        docker --version
        docker compose version
        ```

명령어 차이(참고)
- .env 복사 예시
    - Windows (PowerShell)
        ```powershell
        copy .env.example .env
        ```
    - macOS/Linux (zsh/bash)
        ```bash
        cp .env.example .env
        ```

---

## 빠른 시작

1) 필수 설치 확인
- Docker Desktop 설치 후 버전 확인

2) 저장소 클론 및 환경 파일 준비
```bash
git clone https://github.com/dorae222/hackathon_test.git
cd hackathon_test
```

Windows (PowerShell):
```powershell
copy .env.example .env
```

macOS/Linux (bash/zsh):
```bash
cp .env.example .env
```

3) 빌드 & 실행
```bash
docker compose build
docker compose up -d
```

4) 접속 URL (기본 .env 기준)
- 웹 프론트(Nginx): http://localhost:8085
- Spring Swagger: http://localhost:8081/swagger
- AI Vision Health: http://localhost:8000/health

포트가 이미 사용 중이면 `.env`에서 변경 후 재기동하세요. 예) 기본 8085가 충돌 시 `NGINX_PORT=8090` 등 다른 값으로 설정

문제 시 로그 보기
```bash
# 전체 로그 팔로우
docker compose logs -f

# 서비스별 로그
docker compose logs -f nginx
docker compose logs -f spring
docker compose logs -f ai-vision
docker compose logs -f ai-chatbot
```

---

## 구성 요소와 포트

- nginx: 정적 파일 서빙(frontend/) + 리버스 프록시(컨테이너 80, 호스트 기본 8085)
    - / → 정적 페이지(index.html 등)
    - /api/* → Spring(컨테이너 8080 → 호스트 기본 8081)
    - /ai/chat → ai-chatbot(:8001)/chat
    - /ai/* → ai-vision(:8000)
    - 참고: /ai/chat은 ai-chatbot 서비스로 라우팅됩니다.
- backend-spring: 비즈니스 API 게이트웨이(컨테이너 8080 → 호스트 기본 8081)
 
- ai-vision-service: 이미지 목록/서빙, 분류(기본 8000)
- ai-chatbot: OpenAI 연동 챗 API(기본 8001)

Nginx 프록시 경유 시 챗봇 호출 경로는 `/ai/chat` 입니다. 컨테이너 간 내부 통신은 `http://ai-chatbot:8001` / `http://ai-vision:8000` 을 사용합니다.

모든 포트는 `.env`로 조정할 수 있습니다. 기본값은 `.env.example` 참고.
본 저장소의 기본 설정은 다음과 같습니다(호스트 기준):
- NGINX_PORT=8085 (정적 웹/리버스 프록시)
- SPRING_PORT=8081 (Spring Boot)
- AI_PORT=8000 (ai-vision)

---

## 환경 설정 요약(.env)

- 공통
    - ENV=dev, TZ=Asia/Seoul
    - NGINX_PORT=8085, SPRING_PORT=8081, AI_PORT=8000, AI_CHATBOT_PORT=8001
- Spring → AI 내부 호출 URL
    - AI_BASE_URL=http://ai-vision:8000
- AI Vision(이미지 분류)
    - MODEL_PTH_PATH=/app/models/dog_breed_classifier.pth
    - CLASS_MAP_PATH=/app/models/class_map.json
    - NUM_CLASSES=20
    - TRAIN_ON_START, PRETRAINED, FREEZE_BACKBONE 등은 데모용 옵션
- AI Chatbot(문장 생성)
    - OPENAI_API_KEY= (필요 시 입력)
    - OPENAI_MODEL=gpt-4o-mini

모든 항목의 예시는 `.env.example`를 확인하세요. Windows에서 8080은 종종 다른 프로세스(예: Oracle TNS Listener)가 사용 중일 수 있어 충돌 시 `NGINX_PORT`를 다른 값(예: 8086, 8090 등)으로 변경하세요. 기본값은 8085입니다.

---

## CPU/GPU 실행 가이드

- CPU(기본, 모든 OS):
    - ai-vision은 CPU 전용 PyTorch 휠을 사용해 경량 이미지로 동작합니다.
    - 실행: `docker compose up -d ai-vision`

- GPU(Linux/WSL2, NVIDIA):
    - 사전 조건: NVIDIA 드라이버 + nvidia-container-toolkit 설치
    - GPU 오버레이 사용:
        ```powershell
        docker compose -f docker-compose.yml -f docker-compose.gpu.yml build ai-vision
        docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d ai-vision
        ```
    - 컨테이너 내부에서 `import torch; torch.cuda.is_available()`로 CUDA 인식 확인 가능

- macOS: Docker는 호스트 GPU에 접근할 수 없으므로 CPU로 자동 동작합니다. (도커 밖 네이티브 실행 시 MPS 사용 가능)

---

## 모델 준비와 데모 실행

- 기본 동작: ai-vision은 컨테이너 내 `models/`에 있는 학습된 모델(.pth)과 `class_map.json`을 사용합니다.
- 모델 파일 배치:
    - `ai-vision-service/models/dog_breed_classifier.pth`
    - `ai-vision-service/models/class_map.json`
- 빠른 데모(선택): 모델이 없을 경우, 매우 간단한 셋업으로 임시 학습을 수행할 수 있습니다.
    - `.env`에서 `TRAIN_ON_START=1` 설정 (기본은 0)
    - 샘플 수/에폭 등은 다음 변수로 제어: `MAX_TRAIN_SAMPLES`, `EPOCHS`, `BATCH_SIZE`, `PRETRAINED`, `FREEZE_BACKBONE`
    - 데모 목적 외에는 실제 학습 파이프라인을 권장합니다.

---

## 유용한 엔드포인트 모음

- 브라우저용(through Nginx)
    - 이미지 분류: POST /api/v1/dogs/classify (multipart: file, top_k)
    - 유사 이미지 검색: POST /api/v1/dogs/search-similar (multipart: file, top_k)
    - 입양 문구 생성: POST /api/v1/text/adoption-copy (JSON)
    - 챗봇: POST /ai/chat (OpenAI 필요)
- 개발 편의(직접 접근)
    - AI Health: GET /ai/health
    - 이미지/동물 데이터: GET /ai/animals, GET /ai/images/{filename}

자세한 API는 위키의 “02-API-Spec”을 참고하세요.

---

## 트러블슈팅 요약

- 502 Bad Gateway: 대상 서비스 컨테이너 상태 및 로그 확인 → 재시작
- 8000/8081/8085 포트 충돌: `.env`에서 포트 변경 후 재시작
- OpenAI 오류: `OPENAI_API_KEY` 설정 여부, 요청량 및 네트워크 점검

### Windows에서 8080(또는 특정 포트) 충돌 해결

1) 어떤 프로세스가 점유 중인지 확인

```powershell
netstat -aon | Select-String ":8080"
```

2) 출력의 마지막 열(PID)을 확인한 후, 강제 종료(일반 프로세스인 경우)

```powershell
taskkill /PID <PID> /F
```

3) 서비스가 점유 중(IIS 등)이라면 서비스 중지 후 재시작

```powershell
Get-Service W3SVC | Stop-Service -Force
# 필요 시 다시 시작: Get-Service W3SVC | Start-Service
```

4) 컨테이너 재시작

```powershell
docker compose down
docker compose up -d
```

---

## 크레딧

- Backend: Spring Boot
- AI Vision: FastAPI + PyTorch
- AI Chatbot: FastAPI + OpenAI
- Infra: Docker Compose, Nginx
