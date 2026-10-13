"""Glamira pipeline: GCS -> BigQuery raw, then dbt models (one Airflow task per model, Cosmos).

The export task (Mongo -> GCS on the VM) is added before the load group in a later step.
"""
from datetime import datetime
from pathlib import Path

from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.sdk import TaskGroup, dag, task
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import InvocationMode

PROJECT = "glamira-analytics-511114"
BUCKET = f"{PROJECT}-raw"                     # terraform: "${var.project_id}-raw"
LOCATION = "asia-southeast1"
TABLES = ["summary", "ip_locations", "products"]

DBT_PROJECT = Path("/opt/airflow/transform")   # mounted from ../transform
DBT_EXECUTABLE = "/opt/dbt-venv/bin/dbt"      # separate venv, see Dockerfile

# Reuses transform/profiles.yml (oauth); credentials come from the mounted ~/.config/gcloud.
profile = ProfileConfig(
    profile_name="transform",
    target_name="dev",
    profiles_yml_filepath=DBT_PROJECT / "profiles.yml",
)


@task
def latest_export(table: str) -> list[str]:
    """Return the Parquet glob of the newest complete export run, e.g. export/summary/<run_id>/part-*.parquet.

    A run is complete once mongo_to_gcs.py has written its _SUCCESS marker.
    """
    markers = GCSHook().list(BUCKET, prefix=f"export/{table}/", match_glob="**/_SUCCESS")
    if not markers:
        raise ValueError(f"No complete export for {table} in gs://{BUCKET}/export/{table}/")
    run_dir = max(markers).rsplit("/", 1)[0]   # run_ids are timestamps, so max = newest
    return [f"{run_dir}/part-*.parquet"]


@dag(
    schedule=None,          # manual for now: the source data is a fixed 2020 snapshot
    start_date=datetime(2026, 10, 1),
    catchup=False,
    tags=["glamira", "dbt"],
)
def glamira_pipeline():
    with TaskGroup("load") as load:
        for table in TABLES:
            GCSToBigQueryOperator(
                task_id=table,
                bucket=BUCKET,
                source_objects=latest_export.override(task_id=f"find_{table}")(table),
                destination_project_dataset_table=f"{PROJECT}.raw.{table}",
                source_format="PARQUET",
                src_fmt_configs={"enableListInference": True},   # nested lists load as ARRAY, not wrapper structs
                write_disposition="WRITE_TRUNCATE",               # same as bq load --replace
                location=LOCATION,
            )

    dbt = DbtTaskGroup(
        group_id="dbt",
        project_config=ProjectConfig(DBT_PROJECT, install_dbt_deps=False),   # no dbt packages
        profile_config=profile,
        # SUBPROCESS: dbt lives in its own venv, so Cosmos calls the binary instead of
        # importing dbt into Airflow's Python.
        execution_config=ExecutionConfig(
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
        # Cosmos runs `dbt ls` at parse time to find the models; same binary, same mode.
        render_config=RenderConfig(
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
    )

    load >> dbt


glamira_pipeline()
