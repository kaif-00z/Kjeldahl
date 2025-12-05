# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

import logging
from contextlib import asynccontextmanager
from traceback import format_exc

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, StreamingResponse

from gdrive import AsyncGoogleDriver
from libs.tracker.downloads import DownloadTracker
from models import (
    FileFolderResponse,
    FilesFoldersListResponse,
    Optional,
    SearchResponse,
)

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

global driver
dlt = DownloadTracker()


@asynccontextmanager
async def lifespan(app):
    global driver
    driver = AsyncGoogleDriver()
    await driver._load_accounts()
    yield
    await driver._close_req_session()


app = FastAPI(
    title="Google Drive Mirror",
    summary="High Speed Gdrive Mirror, Indexer & File Streamer Written Asynchronous in Python with FastAPI With Awsome Features & Stablility.",
    version="v0.0.1@beta.3ps",
    lifespan=lifespan,
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
    if not file_id or len(file_id) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file ID format"
        )

    client_ip = request.client.host
    dlt.track_download(file_id, user_ip=client_ip)
    log.info(f"Stream request for file {file_id} from IP {client_ip}")

    try:
        file_info = await driver.get_file_info(file_id)

        if file_info.get("mimeType") == "application/vnd.google-apps.folder":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Feature to download a folder!",
            )
    except HTTPException as err:
        raise err
    except Exception as e:
        log.error(
            f"Unexpected error streaming file {file_id}: {str(e)}\n"
            f"Traceback: {format_exc()}"
        )
        raise HTTPException(
            status_code=getattr(e, "status", status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=getattr(e, "reason", str(e)),
        )

    return await driver.stream_file(
        file_id.strip(), file_info, request.headers.get("Range", 0)
    )


@app.get("/info", response_model=FileFolderResponse)
async def file_info(
    file_id: str = Query(..., description="Google Drive file or folder ID")
):
    try:
        data = await driver.get_file_info(file_id)
        return JSONResponse(
            {
                "success": True,
                "data": data,
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=getattr(
                e.resp, "status", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail={
                "success": False,
                "error": getattr(e, "reason", str(e)),
            },
        )


@app.get("/folders/list", response_model=FilesFoldersListResponse)
async def folders_in_root(
    folder_id: Optional[str] = Query(
        None, description="Google Drive folder ID (optional, defaults to root)"
    ),
    page_size: int = Query(50, ge=1, le=50, description="Number of items per page"),
    page_token: Optional[str] = Query(
        None, description="Pagination token for next page"
    ),
):
    try:
        data = (
            await driver.list_all(page_token=page_token, page_size=page_size)
            if not folder_id
            else await driver.list_all(
                folder_id=folder_id, page_token=page_token, page_size=page_size
            )
        )
        return JSONResponse(
            {
                "success": True,
                "data": data,
            }
        )
    except BaseException as e:
        raise HTTPException(
            status_code=getattr(e, "status", status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail={
                "success": False,
                "error": getattr(e, "reason", str(e)),
            },
        )


@app.get("/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., min_length=3, description="Search query"),
    page_size: int = Query(50, ge=1, le=50, description="Number of results per page"),
    page_token: Optional[str] = Query(
        None, description="Pagination token for next page"
    ),
):
    try:
        data = await driver.search_files_in_drive(
            query, page_token=page_token, page_size=page_size
        )
        return JSONResponse(
            {
                "success": True,
                "data": data,
            }
        )
    except BaseException as e:
        raise HTTPException(
            status_code=getattr(
                e.resp, "status", status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail={
                "success": False,
                "error": getattr(e, "reason", str(e)),
            },
        )
