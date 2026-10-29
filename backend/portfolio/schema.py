from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, StringConstraints, model_validator

# ISO 8601 year, year-month, or full date: "2024", "2024-06", "2024-06-15"
IsoDate = Annotated[str, StringConstraints(pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$")]

HideableField = Literal[
    "contact.email",
    "contact.phone",
    "contact.location",
    "summary",
    "education",
    "experience",
    "projects",
    "skills",
]


class Link(BaseModel):
    label: str
    url: HttpUrl


class Contact(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr | None = None
    phone: str | None = None
    location: str | None = None
    links: list[Link] = []


class Entry(BaseModel):
    organization: str
    title: str | None = None
    location: str | None = None
    start: IsoDate | None = None
    end: IsoDate | None = None
    bullets: list[str] = []

    @model_validator(mode="after")
    def end_after_start(self):
        if self.start and self.end:
            n = min(len(self.start), len(self.end))
            if self.end[:n] < self.start[:n]:
                raise ValueError("end date is before start date")
        return self


class Project(BaseModel):
    name: str
    description: str | None = None
    url: HttpUrl | None = None
    bullets: list[str] = []


class Resume(BaseModel):
    contact: Contact
    summary: str | None = None
    education: list[Entry] = []
    experience: list[Entry] = []
    projects: list[Project] = []
    skills: list[str] = []
    hidden_fields: list[HideableField] = []
