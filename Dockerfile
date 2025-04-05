FROM python:3.11-slim

WORKDIR /app
COPY bot /app

RUN pip install discord.py aiohttp

CMD ["python", "main.py"]
