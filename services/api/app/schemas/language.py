from pydantic import BaseModel, ConfigDict


class LanguageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    is_source_enabled: bool
    is_target_enabled: bool
