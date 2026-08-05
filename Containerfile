FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot

RUN useradd --create-home --uid 1000 bot
USER bot

CMD ["python", "-m", "bot.main"]
