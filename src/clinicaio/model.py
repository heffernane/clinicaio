from pydantic import BaseModel, ConfigDict

class Model(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        #use_enum_values=True,
        validate_default=True,
        arbitrary_types_allowed=True,
    )