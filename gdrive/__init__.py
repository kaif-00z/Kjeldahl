# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# inspired from https://gitlab.com/GoogleDriveIndex/Google-Drive-Index (serverless JS)

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

import base64
import json
import mimetypes
import os
import pickle
import random
import time
import re
from glob import glob
from logging import WARNING, getLogger

import aiofiles
import aiohttp
import jwt
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from libs.time_cache import timed_cache

from .config import Var
from .errors import *
from .utils import asyncio, run_async

LOGGER = getLogger(__name__)


class AsyncGoogleDriver:
    def __init__(self):
        self._requests_sessions = aiohttp.ClientSession()

        # for service accounts
        self.__service_accounts_data = {}
        self.__service_accounts_identifiers = []
        # for normal account
        self.__credntials = None

    async def _async_searcher(
        self,
        url: str,
        post: bool = None,
        headers: dict = None,
        params: dict = None,
        json: dict = None,
        data: dict = None,
        ssl=None,
        *args,
        **kwargs,
    ) -> dict:
        if post:
            data = await self._requests_sessions.post(
                url, headers=headers, json=json, data=data, ssl=ssl, *args, **kwargs
            )
        else:
            data = await self._requests_sessions.get(
                url, headers=headers, params=params, ssl=ssl, *args, **kwargs
            )

        try:
            return await data.json()
        except BaseException as err:
            return {
                "error": "unable_to_fetch_data",
                "error_description": "Unable to get json data",
                "error_details": str(err),
            }

    async def _load_accounts(self) -> None:
        if Var.IS_SERVICE_ACCOUNT:
            procs = [self._lazy_load_sa(sa) for sa in glob("accounts/*.json")]
            await asyncio.gather(*procs)
        elif os.path.exists("token.pickle"):
            await self._lazy_load_pickle()

    async def _lazy_load_pickle(self) -> None:
        async with aiofiles.open("token.pickle", "rb") as t:
            data = pickle.loads(await t.read())
            self.__credntials = {
                "client_id": data.client_id,
                "client_secret": data.client_secret,
                "refresh_token": data.refresh_token,
                "grant_type": "refresh_token",
            }
            return self.__credntials

    async def _lazy_load_sa(self, file_path: str) -> dict:
        if data := self.__service_accounts_data.get(file_path):
            return
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            self.__service_accounts_data[file_path] = base64.b64encode(
                json.dumps(data).encode()
            ).decode()
            return

    @run_async
    def _generate_gcp_jwt(self, sa_json) -> str:
        now = int(time.time())
        private_key = sa_json["private_key"]
        client_email = sa_json["client_email"]
        payload = {
            "iss": client_email,
            "scope": "https://www.googleapis.com/auth/drive",
            "aud": "https://www.googleapis.com/oauth2/v4/token",
            "exp": now + 3600,
            "iat": now,
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    # actually both sa's access token and pickle's refresh token expire after 1hr or 3600s
    # so caching it for 58mins :)
    @timed_cache(seconds=3500)
    async def _fetch_token(
        self, credentials: str = None, is_service_account: bool = False
    ) -> str:

        if is_service_account and credentials:
            credentials = json.loads(base64.b64decode(credentials).decode())
            _jwt_payload = await self._generate_gcp_jwt(credentials)
            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": _jwt_payload,
            }
        else:
            payload = await self._lazy_load_pickle()

        for i in range(3):
            res = await self._async_searcher(
                url="https://www.googleapis.com/oauth2/v4/token",
                post=True,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=payload,
            )
            if at := (res or {}).get("access_token"):
                return at

        raise FailedToFetchToken(details=res)

    async def _get_token(self, retry: int = 0) -> str:
        if self.__credntials:
            return await self._fetch_token()

        if Var.IS_SERVICE_ACCOUNT and self.__service_accounts_data:
            if not self.__service_accounts_identifiers:
                self.__service_accounts_identifiers = list(
                    self.__service_accounts_data.keys()
                )
            sad = self.__service_accounts_data[
                random.choice(self.__service_accounts_identifiers)
            ]
            try:
                return await self._fetch_token(sad, is_service_account=True)
            except FailedToFetchToken as err:
                if retry >= 5:
                    raise err
                return await self._get_token(retry + 1)

        raise RuntimeError(
            "Neither a service account nor a token.pickle file is available. Please configure authentication first!"
        )

    async def stream_file(
        self, file_id: str, file: dict, range_header: int = 0
    ) -> StreamingResponse:
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&acknowledgeAbuse=true"

        file_name = file["name"]
        file_size = int(file.get("size", 0))
        mime_type = (
            file.get("mimeType")
            or mimetypes.guess_type(file["name"])[0]
            or "application/octet-stream"
        )

        headers = {}

        if range_header:
            headers["Range"] = str(range_header)

        res = None
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=None))
        for i in range(3): # will use recursion in future rather than this ugly for loop
            try:
                headers["Authorization"] = f"Bearer {await self._get_token()}"
                res = await session.get(url, headers=headers)
                if res.status in (200, 206):
                    break
            except Exception as err:
                LOGGER.error(str(err))

            if i >= 2:
                if res is None:
                    raise HTTPException(500, "Unknown error while contacting Google Drive")

                if res.status == 404:
                    raise HTTPException(404, "File Not Found")
                
                if res.status == 401:
                    raise HTTPException(401, "Token is expired!! Please check your authentications.")
                
                if res.status == 429:
                    raise HTTPException(429, "Rate limit exceeded! use service accounts or add more to avoid this.")

                details = await res.text()

                if res.status == 403:
                    raise HTTPException(403, details)

                if res.status not in (200, 206):
                    raise HTTPException(res.status, details)

        async def stream():
            try:
                async for chunk in res.content.iter_chunked(1024 * 1024):
                    if chunk:
                        yield chunk
            except BaseException as e:
                if isinstance(e, asyncio.CancelledError):
                    LOGGER.warning(
                        f"Client disconnected while streaming file {file_id}"
                    )
                else:
                    LOGGER.error(f"Stream error: {e}")
                raise
            finally:
                await session.close()

        response = StreamingResponse(content=stream(), media_type=mime_type)

        response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'

        if not range_header and file_size:
            response.headers["Content-Length"] = str(file_size)

        if res.status == 206:
            response.status_code = 206
            for h in ["Content-Range", "Accept-Ranges"]:
                if h in res.headers:
                    response.headers[h] = res.headers[h]
        else:
            response.status_code = 200

        return response

    @timed_cache(seconds=3600)  # 1hr is good for this as well
    async def get_file_info(self, file_id) -> dict:

        params = {
            "supportsAllDrives": "true",
            "fields": "id,name,mimeType,size,createdTime,modifiedTime,thumbnailLink,fileExtension",
        }

        headers = {
            "Authorization": f"Bearer {await self._get_token()}",
            "Accept": "application/json",
        }

        for i in range(3):
            res = await self._async_searcher(
                url=f"https://www.googleapis.com/drive/v3/files/{file_id}/",
                headers=headers,
                params=params,
            )

            if (res or {}).get("id"):
                return res

        raise FailedToFetchFileInfo(details=res)

    @timed_cache(seconds=300)  # 5 mins
    async def list_all(
        self,
        folder_id: str = Var.ROOT_FOLDER_ID,
        page_token: str = None,
        page_size: int = 50,
    ) -> dict:

        params = {
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "q": (
                f"'{folder_id}' in parents AND trashed = false "
                "AND mimeType != 'application/vnd.google-apps.shortcut'"
            ),
            "spaces": "drive",
            "pageSize": page_size,
            "fields": "nextPageToken, files(id,name,mimeType,size,createdTime,modifiedTime,thumbnailLink,fileExtension)",
            "orderBy": "folder, name",
        }

        if page_token:
            params["pageToken"] = page_token

        headers = {
            "Authorization": f"Bearer {await self._get_token()}",
            "Accept": "application/json",
        }

        for i in range(3):
            res = await self._async_searcher(
                url=f"https://www.googleapis.com/drive/v3/files/",
                headers=headers,
                params=params,
            )

            if "files" in (res or {}):
                return res

        raise FailedToFetchFilesTree(details=res)

    @staticmethod
    def _format_search_keyword(keyword):
        if not keyword:
            return ""
        result = re.sub(r'(!=)|[\'"=<>/\\\\:]', '', keyword)
        result = re.sub(r'[,，|(){}]', ' ', result)
        return result.strip()

    @timed_cache(seconds=300)  # 5mins
    async def search_files_in_drive(
        self, query: str, page_token=None, page_size=50
    ) -> dict:
        query = self._format_search_keyword(query)
        words = query.split()
        name_cond = " AND ".join([f"name contains '{w}'" for w in words])

        params = {
            "q": (
                "trashed = false "
                "AND mimeType != 'application/vnd.google-apps.shortcut' "
                "AND mimeType != 'application/vnd.google-apps.document' "
                "AND mimeType != 'application/vnd.google-apps.spreadsheet' "
                "AND mimeType != 'application/vnd.google-apps.form' "
                "AND mimeType != 'application/vnd.google-apps.site' "
                "AND name != '.password' "
                f"AND ({name_cond})"
            ),
            "fields": "nextPageToken, files(id,name,mimeType,size,createdTime,modifiedTime,thumbnailLink,fileExtension)",
            "pageSize": page_size,
            "orderBy": "folder, name, modifiedTime desc",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "corpora": "allDrives",
        }

        headers = {
            "Authorization": f"Bearer {await self._get_token()}",
            "Accept": "application/json",
        }

        if page_token:
            params["pageToken"] = page_token

        for i in range(3):
            res = await self._async_searcher(
                url=f"https://www.googleapis.com/drive/v3/files/",
                headers=headers,
                params=params,
            )

            if "files" in (res or {}):
                return res

        raise FailedToFetchSearchResult(details=res)
