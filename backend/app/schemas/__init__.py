from pydantic import Field, model_validator

from shared.schemas import ContractModel, Language, Mode


class SourceFile(ContractModel):
    path: str = Field(min_length=1, max_length=500)
    language: Language
    code: str = Field(min_length=1, max_length=1000000)


class ScanRequest(ContractModel):
    repository: str = Field(
        default="local/demo", pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    )
    files: list[SourceFile] = Field(min_length=1, max_length=200)
    diff: str | None = Field(default=None, max_length=1000000)
    mode: Mode = "combined"

    @model_validator(mode="after")
    def unique_paths(self) -> "ScanRequest":
        if len({file.path for file in self.files}) != len(self.files):
            raise ValueError("Duplicate source paths")
        return self
