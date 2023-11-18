from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class ConfigSettings(BaseSettings):
    ENV: Optional[str] = Field(None, validation_alias="ENV")
    config_file: str = Field("./config.yaml", validation_alias="CONFIG_FILE_PATH")
