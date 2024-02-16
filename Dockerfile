FROM python:3.10-alpine
WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
RUN python --version
CMD ["python", "starter.py"]
