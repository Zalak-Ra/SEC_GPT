FROM python:3.11-slim

# install nmap (sqlmap and dirsearch come from pip)
RUN apt-get update && apt-get install -y nmap && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && pip install sqlmap dirsearch

COPY . .
RUN mkdir -p logs workspace config

CMD ["python", "main.py"]
