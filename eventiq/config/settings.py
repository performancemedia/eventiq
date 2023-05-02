from typing import Optional

from pydantic import BaseSettings, Field


class ConfigSettings(BaseSettings):
    ENV: Optional[str] = Field(None, env="ENV")
    config_file: str = Field("./config.yaml", env="CONFIG_FILE_PATH")
