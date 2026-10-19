FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY chat_input.py local_agent.py workspace_tools.py .
COPY prompts.md .

CMD ["python", "chat_input.py"]
