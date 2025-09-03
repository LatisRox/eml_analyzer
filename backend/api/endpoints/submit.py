import httpx
from fastapi import APIRouter, HTTPException, status

from backend import dependencies, schemas
from backend.dependencies import OptionalOpenai
from backend.schemas.eml import Attachment, Body, Header
from backend.schemas.openai_chat import ChatPrompt, ChatResponse
from backend.utils import attachment_to_file

router = APIRouter()


@router.post(
    "/inquest",
    response_description="Return a submission result",
    summary="Submit an attachment to InQuest",
    description="Submit an attachment to InQuest",
    status_code=200,
)
async def submit_to_inquest(
    attachment: Attachment, *, optional_inquest: dependencies.OptionalInQuest
) -> schemas.SubmissionResult:
    # check ext type
    valid_types = ["doc", "docx", "ppt", "pptx", "xls", "xlsx"]
    if attachment.extension not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{attachment.extension} is not supported.",
        )

    if optional_inquest is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have the InQuest API key",
        )

    try:
        return await optional_inquest.submit(attachment_to_file(attachment))
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Something went wrong with InQuest submission: {e}",
        ) from e


@router.post(
    "/virustotal",
    response_description="Return a submission result",
    summary="Submit an attachment to VirusTotal",
    description="Submit an attachment to VirusTotal",
    status_code=200,
)
async def submit_to_virustotal(
    attachment: Attachment, *, optional_vt: dependencies.OptionalVirusTotal
) -> schemas.SubmissionResult:
    if optional_vt is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have the VirusTotal API key",
        )

    try:
        await optional_vt.scan_file_async(attachment_to_file(attachment))
        sha256 = attachment.hash.sha256
        return schemas.SubmissionResult(
            reference_url=f"https://www.virustotal.com/gui/file/{sha256}/detection"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Something went wrong with VirusTotal submission: {e}",
        ) from e


# Endpoint for sending custom prompts to OpenAI
@router.post(
    "/chatgpt",
    response_model=ChatResponse,
    response_description="Return an OpenAI response",
    summary="Send a custom prompt to OpenAI",
    description="Send a prompt to the OpenAI Responses API and get the response",
    status_code=status.HTTP_200_OK,
)
async def send_to_chatgpt(
    header: Header,
    body: Body,
    prompt: ChatPrompt,
    optional_openai: OptionalOpenai,
) -> ChatResponse:
    if optional_openai is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have the OpenAI API key",
        )

    try:
        full_prompt = (
            f"{prompt.prompt}\nHeader: {header.header!s}\nBody: {body.content}"
        )
        reply = await optional_openai.send_prompt(
            prompt=full_prompt,
            model=prompt.model,
        )
        return ChatResponse(response=reply)
    except Exception as e:  # pragma: no cover - safety net
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with OpenAI: {e!s}",
        ) from e
