import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from lab4.domain import Laureate
from lab4.pg_repository import PgLaureateRepository
from lab4.repository import ConflictError, LaureateRepository, NotFoundError
from lab4.validators import is_valid_email, is_valid_name

DSN = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)

app = FastAPI(title="Nobel Laureates API")


@lru_cache
def get_repository() -> LaureateRepository:
    # Єдине місце, де вибирається конкретне сховище.
    return PgLaureateRepository(DSN)


Repo = Annotated[LaureateRepository, Depends(get_repository)]


class LaureateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: str = Field(max_length=255)
    birth_year: int = Field(ge=1800, le=2100)
    country_id: int = Field(ge=1)
    prize_ids: list[int] = Field(default_factory=list)

    @field_validator("full_name")
    @classmethod
    def check_name(cls, value: str) -> str:
        if not is_valid_name(value):
            raise ValueError("Invalid name format")
        return value

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        if not is_valid_email(value):
            raise ValueError("Invalid email format")
        return value

    def to_domain(self) -> Laureate:
        return Laureate(**self.model_dump())


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/laureates")
def list_laureates(
    repo: Repo,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Laureate]:
    return repo.list_all(limit, offset)


@app.get("/laureates/{laureate_id}")
def get_laureate(laureate_id: int, repo: Repo) -> Laureate:
    return repo.get(laureate_id)


@app.post("/laureates", status_code=201)
def create_laureate(body: LaureateIn, repo: Repo) -> Laureate:
    return repo.create(body.to_domain())


@app.put("/laureates/{laureate_id}")
def update_laureate(laureate_id: int, body: LaureateIn, repo: Repo) -> Laureate:
    return repo.update(laureate_id, body.to_domain())


@app.delete("/laureates/{laureate_id}", status_code=204)
def delete_laureate(laureate_id: int, repo: Repo) -> Response:
    repo.delete(laureate_id)
    return Response(status_code=204)
