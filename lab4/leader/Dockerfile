FROM python:3.11-slim

WORKDIR /app

COPY leader/ /app/leader/
RUN pip install --no-cache-dir flask requests

EXPOSE 5000
CMD ["python", "-m", "leader.main"]