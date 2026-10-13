FROM apache/airflow:3.3.2

# Cosmos goes into Airflow's own environment. Pinning apache-airflow to the image's
# version stops pip from upgrading Airflow while resolving Cosmos.
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" astronomer-cosmos

# dbt gets its own venv: dbt-bigquery and Airflow's Google provider pin different
# protobuf / google-cloud versions. Same versions as the project's uv.lock.
USER root
RUN python -m venv /opt/dbt-venv \
 && /opt/dbt-venv/bin/pip install --no-cache-dir dbt-core==1.12.5 dbt-bigquery==1.12.1 \
 && chown -R airflow:0 /opt/dbt-venv
USER airflow
