from pydantic import Field

from shared.schemas import ContractModel, Language


class PredictInput(ContractModel):
    code: str = Field(min_length=1, max_length=1000000)
    language: Language = "c"


class BatchInput(ContractModel):
    codes: list[str] = Field(min_length=1, max_length=256)
    language: Language = "c"
