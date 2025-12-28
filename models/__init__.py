# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)


from typing import List, Optional, Union

from pydantic import BaseModel, Field

# Base


class BaseFileFolder(BaseModel):
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, description="Display name")
    mimeType: str = Field(..., description="Mime type")
    createdTime: str = Field(..., description="Creation time")
    modifiedTime: str = Field(..., description="Last modification time")
    size: Optional[str] = Field(None, description="Size in bytes")
    thumbnailLink: Optional[str] = Field(None, description="Thumbnail URL")
    fileExtension: Optional[str] = Field(None, description="File extension")


class BaseModem(BaseModel):
    files: List[BaseFileFolder]
    nextPageToken: Optional[str] = Field(
        None, description="Token for fetching the next page of results"
    )


class FileFoldersListData(BaseModem):
    pass


class SearchData(BaseModem):
    pass


# Trending & Hotness Score Models


class FileStats(BaseModel):
    fileId: str = Field(..., description="Unique identifier of the file")
    downloadCount: Optional[int] = Field(0, description="Total number of downloads")
    firstDownload: Optional[str] = Field(
        None, description="Timestamp of the first download"
    )
    lastDownload: Optional[str] = Field(
        None, description="Timestamp of the last download"
    )
    trendingScore: float = Field(..., description="Calculated trending score")
    hotnessScore: float = Field(..., description="Calculated hotness score")


# Response models


class BaseResponse(BaseModel):
    success: bool = Field(..., description="Operation status")


class FilesFoldersListResponse(BaseResponse):
    data: FileFoldersListData


class FileFolderResponse(BaseResponse):
    data: BaseFileFolder


class SearchResponse(BaseResponse):
    data: SearchData


class FilesStatsResponse(BaseResponse):
    data: List[FileStats]


class FileStatsResponse(BaseResponse):
    data: FileStats
