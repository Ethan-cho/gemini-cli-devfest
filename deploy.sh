#!/bin/bash

docker build --no-cache -f Dockerfile \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/streamlit:v9 .

docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/streamlit:v9

gcloud run deploy streamlit-app \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/streamlit:v9 \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated