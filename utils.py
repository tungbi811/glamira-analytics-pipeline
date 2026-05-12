import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def load_dotenv():
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, os.path.expandvars(value))

def required_env(name):
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def path_env(name):
    value = required_env(name)
    if os.path.isabs(value):
        return value
    return os.path.abspath(os.path.join(PROJECT_ROOT, value))
