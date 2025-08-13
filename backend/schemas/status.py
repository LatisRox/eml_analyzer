from pydantic import Field

from .api_model import APIModel


class Status(APIModel):
    cache: bool = Field(default=False, description="Whether cache is enabled or not")
    vt: bool = Field(
        default=False, description="Whether VirusTotal integration is enabled or not"
    )
    inquest: bool = Field(
        default=False, description="Whether InQuest integration is enabled or not"
    )
    urlscan: bool = Field(
        default=False, description="Whether urlscan.io integration is enabled or not"
    )
    email_rep: bool = Field(
        default=False, description="Whether EmailRep integration is enabled or not"
    )
    #Start of added code
    openai: bool = Field(
        default=False, description="Whether Openai integration is enabled or not"
    )
    #copilot: bool = Field(
    #    default=False, description="Whether copilot integration is enabled or not"
    #)
    #anyrun: bool = Field(
    #    default=False, description="Whether anyrun integration is enabled or not"
    #)
    #End of added code
