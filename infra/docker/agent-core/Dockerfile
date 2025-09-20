FROM python:3.11-slim
WORKDIR /app
COPY ../../agent-core /app/agent-core
COPY ../../schema /app/schema
COPY ../../ontology /app/ontology
RUN pip install --no-cache-dir -e agent-core
# Vault mounted at /vault via compose
CMD ["python","-c","print('agent-core container up; mount /vault externally')"]
