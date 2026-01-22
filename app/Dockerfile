FROM python:3.11-slim

WORKDIR /app

# install curl (needed for ECS container healthCheck)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

#HEALTHCHECK --interval=30s --timeout=3s \
#    CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]
