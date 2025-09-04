import os

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, status
from fastapi.encoders import jsonable_encoder
from loguru import logger
from openai import OpenAI
from pydantic import ValidationError
from redis import Redis

from backend import clients, dependencies, schemas, settings
from backend.factories.eml import EmlFactory
from backend.factories.response import ResponseFactory

router = APIRouter()


async def _analyze(
    file: bytes,
    *,
    spam_assassin: clients.SpamAssassin,
    optional_email_rep: clients.EmailRep | None = None,
    optional_inquest: clients.InQuest | None = None,
    optional_vt: clients.VirusTotal | None = None,
    optional_urlscan: clients.UrlScan | None = None,
) -> schemas.Response:
    try:
        payload = schemas.FilePayload(file=file)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        ) from exc

    response = await ResponseFactory.call(
        payload.file,
        optional_email_rep=optional_email_rep,
        spam_assassin=spam_assassin,
        optional_inquest=optional_inquest,
        optional_urlscan=optional_urlscan,
        optional_vt=optional_vt,
    )

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            logger.debug("Requesting OpenAI response")
            ai_response = client.responses.create(
                model="gpt-4o-mini",
                input="write a haiku about ai",
                store=True,
            )
            if settings.DEBUG:
                logger.debug("OpenAI response: {}", ai_response.output_text)
            for body in response.eml.bodies:
                body.ai_text = ai_response.output_text
        except Exception as exc:
            logger.debug("OpenAI request failed: {}", exc)
    else:
        logger.debug("OPENAI_API_KEY not set; skipping OpenAI call")

    return response


def cache_response(
    redis: Redis,
    response: schemas.Response,
    expire: int = settings.REDIS_EXPIRE,
    key_prefix: str = settings.REDIS_KEY_PREFIX,
):
    ex = expire if expire > 0 else None
    redis.set(f"{key_prefix}:{response.id}", value=response.model_dump_json(), ex=ex)


def get_plaintext_body(eml: schemas.Eml) -> str:
    for body in eml.bodies:
        content_type = body.content_type or ""
        if content_type.startswith("text/plain"):
            return body.content
    return ""


@router.post(
    "/",
    response_description="Return an analysis result",
    summary="Analyze an eml",
    description="Analyze an eml and return an analysis result",
)
async def analyze(
    payload: schemas.Payload,
    *,
    background_tasks: BackgroundTasks,
    spam_assassin: dependencies.SpamAssassin,
    optional_redis: dependencies.OptionalRedis,
    optional_email_rep: dependencies.OptionalEmailRep,
    optional_inquest: dependencies.OptionalInQuest,
    optional_vt: dependencies.OptionalVirusTotal,
    optional_urlscan: dependencies.OptionalUrlScan,
) -> schemas.Response:
    response = await _analyze(
        payload.file.encode(),
        spam_assassin=spam_assassin,
        optional_email_rep=optional_email_rep,
        optional_inquest=optional_inquest,
        optional_urlscan=optional_urlscan,
        optional_vt=optional_vt,
    )

    if optional_redis is not None:
        background_tasks.add_task(
            cache_response, redis=optional_redis, response=response
        )

    return response


@router.post(
    "/file",
    response_description="Return an analysis result",
    summary="Analyze an eml",
    description="Analyze an eml and return an analysis result",
)
async def analyze_file(
    file: bytes = File(...),
    *,
    background_tasks: BackgroundTasks,
    optional_redis: dependencies.OptionalRedis,
    spam_assassin: dependencies.SpamAssassin,
    optional_email_rep: dependencies.OptionalEmailRep,
    optional_inquest: dependencies.OptionalInQuest,
    optional_vt: dependencies.OptionalVirusTotal,
    optional_urlscan: dependencies.OptionalUrlScan,
) -> schemas.Response:
    response = await _analyze(
        file,
        optional_email_rep=optional_email_rep,
        spam_assassin=spam_assassin,
        optional_inquest=optional_inquest,
        optional_urlscan=optional_urlscan,
        optional_vt=optional_vt,
    )

    if optional_redis is not None:
        background_tasks.add_task(
            cache_response, redis=optional_redis, response=response
        )

    return response


@router.post(
    "/body",
    response_description="Return the plaintext body of an eml",
    summary="Get plaintext body",
    description="Return the plaintext body from an eml without additional analysis",
)
async def analyze_body(payload: schemas.Payload) -> dict[str, str]:
    try:
        file_payload = schemas.FilePayload(file=payload.file.encode())
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=jsonable_encoder(exc.errors()),
        ) from exc
    eml = EmlFactory().call(file_payload.file)
    return {"body": get_plaintext_body(eml)}
