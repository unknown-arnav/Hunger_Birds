from pydantic import BaseModel


class UploadSignature(BaseModel):
    cloud_name: str
    api_key: str
    timestamp: int
    signature: str
    folder: str
    # Part of the signed parameter set, so the client must send it back verbatim.
    allowed_formats: str
