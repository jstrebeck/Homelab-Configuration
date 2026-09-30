# KServe storage initializer for models:/ URIs (see README.md).
# Build and push (from this directory):
#   docker build -t 192.168.2.203:5000/mlflow-storage-initializer:0.1.0 .
#   docker push 192.168.2.203:5000/mlflow-storage-initializer:0.1.0
# Standard library only; bump the tag here, in cluster-storage-container.yaml
# and in the README together.
FROM python:3.12.14-slim-trixie
COPY initializer.py /app/initializer.py
USER 65532:65532
ENTRYPOINT ["python", "-u", "/app/initializer.py"]
