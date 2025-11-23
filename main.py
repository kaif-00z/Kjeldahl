# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

import logging
import mimetypes
from traceback import format_exc

from fastapi import FastAPI, Request, Response
from fastapi import HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.openapi.docs import get_swagger_ui_html

from gdrive import get_drive_client
from models import SearchResponse, FileFolderResponse, FilesFoldersListResponse,  Optional
from models import FileNotFound


logging.basicConfig(
    format="%(asctime)s || %(name)s [%(levelname)s] : %(message)s",
    handlers=[
        logging.FileHandler("runtime.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
    level=logging.INFO,
    datefmt="%m/%d/%Y, %H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Google Drive Mirror",
    summary="High Speed Gdrive Mirror, Indexer & File Streamer Written Asynchronous in Python with FastAPI With Awsome Features & Stablility.",
    version="v0.0.1@beta.1ps",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def overridden_swagger():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Google-Drive-Mirror APIs",
        swagger_favicon_url="https://ssl.gstatic.com/docs/doclist/images/drive_2022q3_32dp.png",
    )

@app.get("/dl/{file_id}", include_in_schema=False)
async def stream_handler(request: Request, file_id: str) -> StreamingResponse:
    try:
        if not file_id or len(file_id) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file ID format"
            )
        
        # client_ip = request.client.host
        # log.info(f"Stream request for file {file_id} from IP {client_ip}")

        return await media_streamer(request, file_id)
    except FileNotFound as e:
        log.warning(f"File not found: {file_id}, reason: {getattr(e, 'reason', str(e))}")
        return Response(
            content=f"File not found: {getattr(e, 'reason', 'File does not exist')}",
            status_code=status.HTTP_404_NOT_FOUND
        )
    except ConnectionResetError:
        log.info(f"Client disconnected during stream: {file_id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AttributeError as e:
        log.error(f"Attribute error for file {file_id}: {str(e)}")
        return Response(
            content="Invalid file data structure",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            f"Unexpected error streaming file {file_id}: {str(e)}\n"
            f"Traceback: {format_exc()}"
        )
        return Response(
            content="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


async def media_streamer(request: Request, file_id: str):
    range_header = request.headers.get("Range", 0)
    log.info(
        f"now serving {request.headers.get('X-FORWARDED-FOR')}"
    )

    try:
        client = get_drive_client()
        file_info = await client.get_file_info(file_id)
    except Exception as error:
        raise FileNotFound(error)

    file_size = file_info.get("size")

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = 0
        until_bytes = file_size - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return Response(
            status_code=416,
            content="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    until_bytes = min(until_bytes, file_size - 1)
    req_length = until_bytes - from_bytes + 1

    mime_type = file_info.get("mimeType")
    file_name = file_info.get("name")
    disposition = "attachment"

    if not mime_type:
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    return StreamingResponse(
        status_code=206 if range_header else 200,
        content=client._stream_file(file_id),
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )


@app.get("/info", response_model=FileFolderResponse)
async def file_info(
    file_id: str = Query(..., description="Google Drive file or folder ID")
):
    try:
        client = get_drive_client()
        data = await client.get_file_info(file_id)
        return JSONResponse(
            {
                "success": True,
                "data": data,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=getattr(e.resp, 'status', status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail={
                "success": False,
                "error": getattr(e, 'reason', str(e)),
            }
        )


@app.get("/folders/list", response_model=FilesFoldersListResponse)
async def folders_in_root(
    folder_id: Optional[str] = Query(None, description="Google Drive folder ID (optional, defaults to root)"),
    page_size: int = Query(100, ge=1, le=100, description="Number of items per page"),
    page_token: Optional[str] = Query(None, description="Pagination token for next page")
):
    try:
        client = get_drive_client()
        data, info = (
            await client.list_all(page_token=page_token, page_size=page_size) if not folder_id 
            else await client.list_all(folder_id=folder_id, page_token=page_token, page_size=page_size)
        )
        return JSONResponse(
            {
                "success": True,
                "data": data,
                "additional_info": info
            }
        )
    except BaseException as e:
        raise HTTPException(
            status_code=getattr(e, 'status', status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail={
                "success": False,
                "error": getattr(e, 'reason', str(e)),
            }
        )


@app.get("/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., min_length=3, description="Search query"),
    page_size: int = Query(100, ge=1, le=100, description="Number of results per page"),
    page_token: Optional[str] = Query(None, description="Pagination token for next page")
):
    try:
        client = get_drive_client()
        data, info = await client.search_files_in_drive(query, page_token=page_token, page_size=page_size)
        return JSONResponse(
            {
                "success": True,
                "data": data,
                "additional_info": info
            }
        )
    except BaseException as e:
        raise HTTPException(
            status_code=getattr(e.resp, 'status', status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail={
                "success": False,
                "error": getattr(e, 'reason', str(e)),
            }
        )