import hashlib
from functools import partial

import aiometer
from loguru import logger
from returns.functions import raise_exception
from returns.future import FutureResultE, future_safe
from returns.pipeline import flow
from returns.pointfree import bind
from returns.unsafe import unsafe_perform_io

from backend import clients, schemas, types

from .abstract import AbstractAsyncFactory
from .emailrep import EmailRepVerdictFactory
from .eml import EmlFactory
from .inquest import InQuestVerdictFactory
from .oldid import OleIDVerdictFactory
from .openai import OpenAIVerdictFactory
from .spamassassin import SpamAssassinVerdictFactory
from .urlscan import UrlScanVerdictFactory
from .virustotal import VirusTotalVerdictFactory


def log_exception(exception: Exception):
    logger.exception(exception)


@future_safe
async def parse(eml_file: bytes) -> schemas.Response:
    return schemas.Response(
        eml=EmlFactory().call(eml_file), id=hashlib.sha256(eml_file).hexdigest()
    )


@future_safe
async def get_spam_assassin_verdict(
    eml_file: bytes, *, client: clients.SpamAssassin
) -> schemas.Verdict:
    return await SpamAssassinVerdictFactory(client).call(eml_file)


@future_safe
async def get_oleid_verdict(attachments: list[schemas.Attachment]) -> schemas.Verdict:
    return OleIDVerdictFactory().call(attachments)


@future_safe
async def get_email_rep_verdicts(from_, *, client: clients.EmailRep) -> schemas.Verdict:
    return await EmailRepVerdictFactory(client).call(from_)


@future_safe
async def get_urlscan_verdict(
    urls: types.ListSet[str], *, client: clients.UrlScan
) -> schemas.Verdict:
    return await UrlScanVerdictFactory(client).call(urls)


@future_safe
async def get_inquest_verdict(
    sha256s: types.ListSet[str], *, client: clients.InQuest
) -> schemas.Verdict:
    return await InQuestVerdictFactory(client).call(sha256s)


@future_safe
async def get_vt_verdict(
    sha256s: types.ListSet[str], *, client: clients.VirusTotal
) -> schemas.Verdict:
    return await VirusTotalVerdictFactory(client).call(sha256s)


# start of added code
@future_safe
async def get_openai_verdict(*, client: clients.Openai) -> schemas.Verdict:
    # This calls the new OpenAIVerdictFactory (like VirusTotalVerdictFactory etc.)
    logger.debug("Requesting OpenAI verdict")
    return await OpenAIVerdictFactory(client).call()


# end of added code


@future_safe
async def set_verdicts(
    response: schemas.Response,
    *,
    eml_file: bytes,
    spam_assassin: clients.SpamAssassin,
    optional_email_rep: clients.EmailRep | None = None,
    optional_vt: clients.VirusTotal | None = None,
    optional_urlscan: clients.UrlScan | None = None,
    optional_inquest: clients.InQuest | None = None,
    # start of added code
    optional_openai: clients.Openai | None = None,
    # end of added code
) -> schemas.Response:
    f_results: list[FutureResultE[schemas.Verdict]] = [
        get_spam_assassin_verdict(eml_file, client=spam_assassin),
        get_oleid_verdict(response.eml.attachments),
    ]

    if response.eml.header.from_ is not None and optional_email_rep is not None:
        f_results.append(
            get_email_rep_verdicts(response.eml.header.from_, client=optional_email_rep)
        )

    if optional_vt is not None:
        f_results.append(get_vt_verdict(response.sha256s, client=optional_vt))

    if optional_inquest is not None:
        f_results.append(get_inquest_verdict(response.sha256s, client=optional_inquest))

    # start of added code
    if optional_openai is not None:
        logger.debug("Adding OpenAI verdict to result set")
        f_results.append(get_openai_verdict(client=optional_openai))
    # end of added code

    if optional_urlscan is not None:
        f_results.append(get_urlscan_verdict(response.urls, client=optional_urlscan))

    results = await aiometer.run_all([f_result.awaitable for f_result in f_results])
    values = [
        unsafe_perform_io(result.alt(log_exception).value_or(None))
        for result in results
    ]
    response.verdicts = [value for value in values if value is not None]
    logger.debug("Verdicts ready: {}", [v.name for v in response.verdicts])
    return response


class ResponseFactory(AbstractAsyncFactory):
    @classmethod
    async def call(
        cls,
        eml_file: bytes,
        *,
        spam_assassin: clients.SpamAssassin,
        optional_email_rep: clients.EmailRep | None,
        optional_vt: clients.VirusTotal | None = None,
        optional_urlscan: clients.UrlScan | None = None,
        optional_inquest: clients.InQuest | None = None,
        # start of added code
        optional_openai: clients.Openai | None = None,
        # end of added code
    ) -> schemas.Response:
        f_result: FutureResultE[schemas.Response] = flow(
            parse(eml_file),
            bind(
                partial(
                    set_verdicts,
                    eml_file=eml_file,
                    optional_email_rep=optional_email_rep,
                    spam_assassin=spam_assassin,
                    optional_vt=optional_vt,
                    optional_urlscan=optional_urlscan,
                    optional_inquest=optional_inquest,
                    # start of added code
                    optional_openai=optional_openai,
                    # end of added code
                )
            ),
        )
        result = await f_result.awaitable()
        return unsafe_perform_io(result.alt(raise_exception).unwrap())
