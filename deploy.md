# Google Cloud Run 배포 가이드 (GitHub Codespaces on iPad)

이 문서는 iPad의 GitHub Codespaces 환경에서 Flask API 서버와 Streamlit 프론트엔드 앱을 Google Cloud Run에 배포하는 방법을 단계별로 안내합니다.

## 사전 준비 사항

1.  **Google Cloud 계정 및 프로젝트**:
    *   Google Cloud Platform (GCP) 계정이 필요합니다.
    *   배포를 진행할 GCP 프로젝트를 생성하고 **프로젝트 ID**를 확인합니다.

2.  **GitHub Codespaces**:
    *   현재 작업 환경인 Codespaces가 실행 중이어야 합니다. Codespaces에는 Docker가 이미 설치되어 있어 별도의 설치가 필요 없습니다.

---

## 1단계: Codespaces 환경에 Google Cloud CLI 설치 및 설정

Codespaces 터미널에서 다음 명령어를 순서대로 실행하여 `gcloud` CLI를 설치하고 인증합니다.

### 1.1. gcloud CLI 설치

```bash
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install -y google-cloud-cli
```

### 1.2. gcloud 인증

다음 명령어를 실행하여 GCP 계정을 인증합니다.

```bash
gcloud auth login --no-launch-browser
```

*   명령을 실행하면 터미널에 긴 URL이 나타납니다.
*   **이 URL을 복사**하여 iPad의 웹 브라우저(Safari 등)에 붙여넣고 접속하세요.
*   화면에 나타나는 안내에 따라 Google 계정으로 로그인하고 권한을 허용합니다.
*   인증이 완료되면 브라우저에 **인증 코드**가 표시됩니다. 이 코드를 복사하여 다시 Codespaces 터미널에 붙여넣고 Enter 키를 누릅니다.

### 1.3. gcloud 프로젝트 설정

사용할 GCP 프로젝트를 설정합니다.

```bash
gcloud config set project [YOUR_PROJECT_ID]
```
*`[YOUR_PROJECT_ID]`는 본인의 GCP 프로젝트 ID로 변경하세요.*

### 1.4. 필요한 GCP API 활성화

배포에 필요한 서비스들의 API를 활성화합니다.

```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## 2단계: 백엔드 API 배포 (Flask App)

### 2.1. Artifact Registry 저장소 생성

Docker 이미지를 저장할 저장소를 생성합니다.

```bash
gcloud artifacts repositories create real-estate-repo \
    --repository-format=docker \
    --location=asia-northeast3 \
    --description="Real estate project repository"
```
*(참고: `asia-northeast3`는 서울 리전입니다.)*

### 2.2. API Docker 이미지 빌드 및 푸시

```bash
# 환경 변수 설정
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast3
export REPO_NAME=real-estate-repo
export IMAGE_NAME=api-server

# Docker에 gcloud 인증 설정
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Docker 이미지 빌드 (Dockerfile.api 사용)
docker build -f Dockerfile.api -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:v1 .

# Docker 이미지 푸시
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:v1
```

docker build -f Dockerfile.streamlit \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/streamlit:v1 .

docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/streamlit:v1

gcloud run deploy streamlit-app \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/streamlit:v1 \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated


### 2.3. Cloud Run에 API 서버 배포

```bash
gcloud run deploy api-service \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:v1 \
    --platform managed \
    --region ${REGION} \
    --port 5000 \
    --allow-unauthenticated
```

배포가 완료되면 출력되는 **서비스 URL**을 복사하여 보관하세요. (예: `https://api-service-xxxxxxxxxx-an.a.run.app`)

---

## 3단계: 프론트엔드 앱 배포 (Streamlit App)

### 3.1. Streamlit Docker 이미지 빌드 및 푸시

```bash
# 환경 변수 설정 (이미지 이름만 변경)
export IMAGE_NAME=streamlit-app

# Docker 이미지 빌드 (Dockerfile.streamlit 사용)
docker build -f Dockerfile.streamlit -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:v1 .

# Docker 이미지 푸시
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:v1
```

### 3.2. Cloud Run에 Streamlit 앱 배포

```bash
# [백엔드_API_URL] 부분을 2.3 단계에서 복사한 URL로 반드시 교체하세요.
export BACKEND_API_URL="[백엔드_API_URL]/api/properties"

gcloud run deploy streamlit-service \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:v1 \
    --platform managed \
    --region ${REGION} \
    --port 8501 \
    --set-env-vars FLASK_API_URL=${BACKEND_API_URL} \
    --allow-unauthenticated
```

---

## 4단계: 서비스 접속

프론트엔드 배포가 완료되면 터미널에 최종 서비스 URL이 출력됩니다. 이 URL이 최종 결과물입니다. iPad의 웹 브라우저에서 이 주소로 접속하여 서비스가 정상적으로 작동하는지 확인합니다.