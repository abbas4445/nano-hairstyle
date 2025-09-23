#!/usr/bin/env python3
"""Simple helper script to deploy the chatbot app to Google Cloud Run.

The script expects a `.env` file in the project root. It reads the required
settings and then calls the `gcloud` CLI to deploy the service.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict

ENV_FILE = Path('.env')
REQUIRED_DEPLOY_KEYS = ('GCP_PROJECT_ID', 'CLOUD_RUN_SERVICE', 'CLOUD_RUN_REGION')


def load_env(path: Path) -> Dict[str, str]:
    """Parse a minimal .env style file into a dictionary."""
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}.")

    entries: Dict[str, str] = {}
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' not in line:
            raise ValueError(f"Cannot parse line in .env: {raw_line}")
        key, value = line.split('=', 1)
        entries[key.strip()] = value.strip()
    return entries


def find_gcloud() -> str:
    """Return the absolute path to the gcloud CLI, if available."""
    candidates = [
        shutil.which('gcloud'),
        shutil.which('gcloud.cmd'),
        shutil.which('gcloud.exe'),
    ]
    for candidate in candidates:
        if candidate:
            return candidate
    raise RuntimeError(
        'gcloud CLI is not installed or not on PATH. Install the Google Cloud SDK '
        'from https://cloud.google.com/sdk/docs/install and run `gcloud init` before trying again.'
    )


def run_command(command: list[str]) -> None:
    """Run a shell command and stream its output."""
    print('\n$ ' + ' '.join(command))
    subprocess.run(command, check=True)


def main() -> None:
    print('Loading settings from .env ...')
    env_values = load_env(ENV_FILE)

    missing = [key for key in REQUIRED_DEPLOY_KEYS if not env_values.get(key)]
    if missing:
        joined = ', '.join(missing)
        raise SystemExit(
            f"Missing required deployment settings in .env: {joined}. "
            'Please add them and run the script again.'
        )

    gcloud_path = find_gcloud()

    project_id = env_values['GCP_PROJECT_ID']
    service_name = env_values['CLOUD_RUN_SERVICE']
    region = env_values['CLOUD_RUN_REGION']

    # Keep deployment-only keys out of the runtime environment variables.
    runtime_env = {
        key: value
        for key, value in env_values.items()
        if value and key not in REQUIRED_DEPLOY_KEYS
    }

    env_flag = ''
    if runtime_env:
        env_flag = ','.join(f"{key}={value}" for key, value in runtime_env.items())

    print('Deploying to Google Cloud Run ...')
    command = [
        gcloud_path,
        'run', 'deploy',
        service_name,
        '--project', project_id,
        '--region', region,
        '--platform', 'managed',
        '--source', '.',
        '--allow-unauthenticated',
    ]

    if env_flag:
        command.extend(['--set-env-vars', env_flag])

    try:
        run_command(command)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error

    print('\nDeployment finished!')
    print('You can now check the service URL shown above in the gcloud output.')


if __name__ == '__main__':
    try:
        main()
    except (FileNotFoundError, ValueError, RuntimeError, SystemExit) as exc:
        print(f'Error: {exc}')
        sys.exit(1)