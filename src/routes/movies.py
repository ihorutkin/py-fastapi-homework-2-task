from datetime import timedelta, date
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import get_db, MovieModel
from database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from schemas.movies import (
    MovieListResponseSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
)

router = APIRouter()

# Write your code here


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_all_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    total_items = await db.scalar(select(func.count()).select_from(MovieModel))

    if not total_items:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = ceil(total_items / per_page)

    if page > total_pages:
        raise HTTPException(status_code=404, detail="No movies found.")

    result = await db.execute(
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    movies = result.scalars().all()

    prev_page = (
        f"/theater/movies/?page={page-1}&per_page={per_page}" if page > 1 else None
    )
    next_page = (
        f"/theater/movies/?page={page+1}&per_page={per_page}"
        if page < total_pages
        else None
    )

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema, status_code=200)
async def get_movie_by_id(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel)
        .options(
            joinedload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    return movie


async def get_entities(
    model,
    names: list[str],
    db: AsyncSession,
):
    if not names:
        return []
    existing = (
        (await db.execute(select(model).where(model.name.in_(names)))).scalars().all()
    )

    founds = {obj.name: obj for obj in existing}
    new_objs = [model(name=name) for name in names if name not in founds]

    for obj in new_objs:
        db.add(obj)
    if new_objs:
        await db.flush()

    return list(founds.values()) + new_objs


@router.post("/movies/", response_model=MovieDetailSchema, status_code=201)
async def create_movie(payload: MovieCreateSchema, db: AsyncSession = Depends(get_db)):
    if payload.date > date.today() + timedelta(days=365):
        raise HTTPException(status_code=400, detail="Invalid input data")

    duplication = await db.scalar(
        select(MovieModel).where(
            MovieModel.name == payload.name,
            MovieModel.date == payload.date,
        )
    )

    if duplication:
        raise HTTPException(
            status_code=409,
            detail=f"A movie with the name '{payload.name}' and release date '{payload.date}' already exists.",
        )

    country_item = await db.scalar(
        select(CountryModel).where(CountryModel.code == payload.country)
    )

    if country_item is None:
        country_item = CountryModel(code=payload.country)
        db.add(country_item)
        await db.flush()

    genres_items = await get_entities(model=GenreModel, names=payload.genres, db=db)
    actors_items = await get_entities(model=ActorModel, names=payload.actors, db=db)
    languages_items = await get_entities(
        model=LanguageModel, names=payload.languages, db=db
    )

    new_film = MovieModel(
        name=payload.name,
        date=payload.date,
        score=payload.score,
        overview=payload.overview,
        status=payload.status,
        budget=payload.budget,
        revenue=payload.revenue,
        country=country_item,
        genres=genres_items,
        actors=actors_items,
        languages=languages_items,
    )
    db.add(new_film)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The input data is invalid (e.g., missing required fields, invalid values).",
        )

    return new_film


@router.delete("/movies/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", status_code=200)
async def update_movie(
    movie_id: int, payload: MovieUpdateSchema, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(movie, field, value)

    try:
        await db.commit()
        await db.refresh(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")

    return {"detail": "Movie updated successfully."}
