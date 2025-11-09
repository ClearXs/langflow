import gzip
import json
from typing import Any

import orjson
from fastapi import Response
from fastapi.encoders import jsonable_encoder


def compress_response(data: Any) -> Response:
    """Compress data and return it as a FastAPI Response with appropriate headers.

    Uses orjson for 2-3x faster JSON serialization compared to standard json.dumps().
    orjson returns bytes directly, eliminating the need for .encode("utf-8").
    """
    # Use orjson for faster serialization (already a project dependency)
    json_data = orjson.dumps(jsonable_encoder(data))

    compressed_data = gzip.compress(json_data, compresslevel=6)

    return Response(
        content=compressed_data,
        media_type="application/json",
        headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding", "Content-Length": str(len(compressed_data))},
    )
