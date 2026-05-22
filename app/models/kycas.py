"""Model representing the "Know Your Class and Section" data returned after successful authentication."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class KYCASModel(BaseModel):
    """Model representing the "Know Your Class and Section" data."""

    model_config = ConfigDict(strict=True, alias_generator=to_camel, populate_by_name=True)

    prn: str | None = Field(
        None,
        title="PRN",
        description="PRN of the user.",
        json_schema_extra={"example": "PESXXYYZZZZZ"},
    )
    srn: str | None = Field(
        None,
        title="SRN",
        description="SRN of the user.",
        json_schema_extra={"example": "PESXXUGYYZZZ"},
    )
    name: str | None = Field(
        None,
        title="Name",
        description="Full name of the user.",
        json_schema_extra={"example": "John Doe"},
    )
    semester: str | None = Field(
        None,
        title="Semester",
        description="Semester the user belongs to.",
        json_schema_extra={"example": "Sem-X"},
    )
    section: str | None = Field(
        None,
        title="Section",
        description="Section the user belongs to.",
        json_schema_extra={"example": "Section X"},
    )
    cycle: str | None = Field(
        None,
        title="Cycle",
        description="Cycle the user belongs to.",
        json_schema_extra={"example": "NA"},
    )
    department: str | None = Field(
        None,
        title="Department",
        description="Department the user belongs to.",
        json_schema_extra={"example": "Computer Science and Engineering"},
    )
    branch: str | None = Field(
        None,
        title="Branch",
        description="Abbreviation of the branch that the user is pursuing.",
        json_schema_extra={"example": "CSE"},
    )
    institute_name: str | None = Field(
        None,
        title="Institute Name",
        description="Institute the user belongs to.",
        json_schema_extra={"example": "PES University"},
    )
