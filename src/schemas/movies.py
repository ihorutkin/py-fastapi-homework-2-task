# Write your code here
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import date, timedelta

from database.models import MovieStatusEnum


class GenreBase(BaseModel):
    id: int
    name: str


class ActorBase(BaseModel):
    id: int
    name: str


class CountryBase(BaseModel):
    id: int
    code: str
    name: Optional[str] = None


class LanguageBase(BaseModel):
    id: int
    name: str


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int


class MovieCreateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: MovieStatusEnum
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str
    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date", mode="after")
    @classmethod
    def validate_date(cls, payload_date: date):
        if payload_date > date.today() + timedelta(days=365):
            raise ValueError("Invalid input data")
        return payload_date


class MovieDetailSchema(MovieListItemSchema):
    model_config = ConfigDict(from_attributes=True)

    status: str
    budget: float
    revenue: float
    country: CountryBase
    genres: list[GenreBase]
    actors: list[ActorBase]
    languages: list[LanguageBase]


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[MovieStatusEnum] = None
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)
