FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY frontend/ frontend/
ENV PORT=10000
EXPOSE $PORT
CMD uvicorn backend.app:app --host 0.0.0.0 --port $PORT
