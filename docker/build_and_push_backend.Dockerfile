# Note: syntax directive removed to avoid network timeout issues
# BuildKit features will still be available when enabled via DOCKER_BUILDKIT=1

ARG LANGFLOW_IMAGE
FROM $LANGFLOW_IMAGE

RUN rm -rf /app/.venv/langflow/frontend

CMD ["python", "-m", "langflow", "run", "--host", "0.0.0.0", "--port", "7860", "--backend-only"]
