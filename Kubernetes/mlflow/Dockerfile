# MLflow tracking server image for the cluster.
# Build and push (from this directory):
#   docker build -t 192.168.2.203:5000/mlflow:3.16.1 .
#   docker push 192.168.2.203:5000/mlflow:3.16.1
# The tag must match the MLflow version below and the image in mlflow.yaml.
# Upstream image ships MLflow and its pinned deps; add the Postgres driver and
# boto3 (needed once artifacts move to S3 on SeaweedFS).
FROM ghcr.io/mlflow/mlflow:v3.16.1
RUN pip install --no-cache-dir psycopg2-binary==2.9.13 boto3==1.43.104
