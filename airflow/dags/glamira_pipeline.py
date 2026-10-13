"""Glamira pipeline: dbt models in BigQuery, one Airflow task per model (Cosmos).

Export (Mongo -> GCS) and load (GCS -> BigQuery raw) tasks are added before the
dbt group in later steps.
"""
from datetime import datetime
from pathlib import Path

from airflow.sdk import dag
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import InvocationMode

DBT_PROJECT = Path("/opt/airflow/transform")   # mounted from ../transform
DBT_EXECUTABLE = "/opt/dbt-venv/bin/dbt"      # separate venv, see Dockerfile

# Reuses transform/profiles.yml (oauth); credentials come from the mounted ~/.config/gcloud.
profile = ProfileConfig(
    profile_name="transform",
    target_name="dev",
    profiles_yml_filepath=DBT_PROJECT / "profiles.yml",
)


@dag(
    schedule=None,          # manual for now: the source data is a fixed 2020 snapshot
    start_date=datetime(2026, 10, 1),
    catchup=False,
    tags=["glamira", "dbt"],
)
def glamira_pipeline():
    DbtTaskGroup(
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


glamira_pipeline()
