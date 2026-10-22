FROM node:22.16.0-alpine3.22 AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install --ignore-scripts
COPY frontend/ ./
ARG VITE_API_URL=http://localhost:8000
ARG VITE_USE_MOCKS=false
ARG VITE_MLFLOW_URL=http://localhost:5001
ENV VITE_API_URL=$VITE_API_URL VITE_USE_MOCKS=$VITE_USE_MOCKS VITE_MLFLOW_URL=$VITE_MLFLOW_URL
RUN npm run build
FROM nginxinc/nginx-unprivileged:1.28.0-alpine
COPY --from=build /app/dist /usr/share/nginx/html
ARG VITE_API_URL=http://localhost:8000
ENV CODESENTINEL_API_ORIGIN=$VITE_API_URL NGINX_ENVSUBST_FILTER=^CODESENTINEL_API_ORIGIN$
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
USER 101
EXPOSE 8080
