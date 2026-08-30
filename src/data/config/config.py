import yaml
from pathlib import Path

def main_config():

    script_dir = Path(__file__).parent

    config_path = script_dir / "config.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    return config