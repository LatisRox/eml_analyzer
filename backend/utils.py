import base64
import typing
import urllib.parse
from io import BytesIO
from typing import Any

import html2text
from bs4 import BeautifulSoup
from ioc_finder import parse_urls

from backend.schemas.eml import Attachment


def is_html(content_type: str) -> bool:
    return "text/html" in content_type


def unpack_safelink_url(url: str) -> str:
    # convert a Microsoft safelink back to a normal URL
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith(".safelinks.protection.outlook.com"):
        parsed_query = urllib.parse.parse_qs(parsed.query)
        safelink_urls = parsed_query.get("url")
        if safelink_urls is not None:
            return urllib.parse.unquote(safelink_urls[0])

    return url


def unpack_safelink_urls(urls: typing.Iterable[str]) -> set[str]:
    return {unpack_safelink_url(url) for url in urls}


def normalize_url(url: str):
    # remove ] and > from the end of the URL
    url = url.rstrip(">")
    return url.rstrip("]")


def normalize_urls(urls: typing.Iterable[str]) -> set[str]:
    return {normalize_url(url) for url in urls}


def get_href_links(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = {str(link.get("href")) for link in soup.findAll("a")}
    return {
        link
        for link in links
        if link.startswith("http://") or link.startswith("https://")
    }


def parse_urls_from_body(content: str, content_type: str) -> set[str]:
    urls: set[str] = set()

    if is_html(content_type):
        # extract href links
        urls.update(get_href_links(content))

        # convert HTML to text
        h = html2text.HTML2Text()
        h.ignore_links = True
        content = h.handle(content)

    urls.update(parse_urls(content, parse_urls_without_scheme=False))
    return normalize_urls(unpack_safelink_urls(urls))


def is_truthy(v: Any) -> bool:
    if v is None:
        return False

    if isinstance(v, bool):
        return v is True

    if isinstance(v, int):
        return v > 0

    try:
        return str(v).upper() == "YES"
    except Exception:
        return False


def attachment_to_file(attachment: Attachment) -> BytesIO:
    bytes_ = base64.b64decode(attachment.raw)

    file_like = BytesIO(bytes_)
    file_like.name = attachment.filename
    return file_like
