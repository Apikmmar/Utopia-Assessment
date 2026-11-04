from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True)


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, from_attributes=True)


__all__ = ["RequestModel", "ResponseModel"]
