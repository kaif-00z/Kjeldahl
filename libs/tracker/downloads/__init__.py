# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

import math
from datetime import datetime, timedelta

import aiosqlite

from gdrive.utils import asyncio
from libs.time_cache import timed_cache


class Algorithms:
    TRENDING = "trendingScore"
    HOTNESS = "hotnessScore"


class DownloadTracker:
    def __init__(self, db_path="downloads.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT,
                    user_ip TEXT,
                    timestamp TEXT
                )
            """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    file_id TEXT PRIMARY KEY,
                    download_count INTEGER DEFAULT 0,
                    first_download TEXT,
                    last_download TEXT
                )
            """
            )

            await db.commit()

    async def track_download(self, file_id: str, user_ip: str = None):
        timestamp = datetime.now().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO downloads (file_id, user_ip, timestamp) VALUES (?, ?, ?)",
                (file_id, user_ip, timestamp),
            )
            cursor = await db.execute(
                "SELECT download_count FROM files WHERE file_id = ?", (file_id,)
            )
            row = await cursor.fetchone()

            if row:
                await db.execute(
                    """
                    UPDATE files
                    SET download_count = download_count + 1,
                        last_download = ?
                    WHERE file_id = ?
                """,
                    (timestamp, file_id),
                )

            else:
                await db.execute(
                    """
                    INSERT INTO files (file_id, download_count, first_download, last_download)
                    VALUES (?, 1, ?, ?)
                """,
                    (file_id, timestamp, timestamp),
                )

            await db.commit()

    async def _calculate_velocity(self, file_id: str, hours: int) -> float:
        cutoff = datetime.now() - timedelta(hours=hours)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM downloads WHERE file_id = ? AND timestamp >= ?",
                (file_id, cutoff.isoformat()),
            )
            row = await cursor.fetchone()

        recent = row[0] if row else 0
        return recent / hours if hours > 0 else 0.0

    async def calculate_trending_score(self, file_id: str) -> float:

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT download_count, first_download, last_download FROM files WHERE file_id = ?",
                (file_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return 0.0

        total_downloads, first_dl, last_dl = row

        # Velocity calculations
        velocity_24 = await self._calculate_velocity(file_id, 24)
        velocity_1 = await self._calculate_velocity(file_id, 1)
        velocity_score = (velocity_24 * 1.0) + (velocity_1 * 5.0)

        popularity_score = math.sqrt(total_downloads)

        # Recency decay
        recency_weight = 0.0
        if last_dl:
            last = datetime.fromisoformat(last_dl)
            hours = (datetime.now() - last).total_seconds() / 3600
            recency_weight = math.exp(-0.693 * hours / 48)

        # Freshness boost
        freshness_boost = 1.0
        if first_dl:
            first = datetime.fromisoformat(first_dl)
            hours = (datetime.now() - first).total_seconds() / 3600
            if hours < 72:
                freshness_boost = 2.0 - (hours / 72)

        return (
            (velocity_score * 3.0 + popularity_score) * recency_weight * freshness_boost
        )

    async def calculate_hotness_score(
        self, file_id: str, gravity: float = 1.5
    ) -> float:

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT download_count, first_download FROM files WHERE file_id = ?",
                (file_id,),
            )
            row = await cursor.fetchone()

        if not row:
            return 0.0

        downloads, first_dl = row
        first = datetime.fromisoformat(first_dl)
        hours_old = (datetime.now() - first).total_seconds() / 3600

        return (downloads / math.pow(hours_old + 2, gravity)) * 1000

    @timed_cache(seconds=300)
    async def get_files_stats(self, limit: int = 10, method: str = Algorithms.TRENDING):
        results = []

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT file_id FROM files")
            rows = await cursor.fetchall()

        file_ids = [row[0] for row in rows]

        async def process(file_id):
            stats = await self.get_file_stats(file_id)
            if stats:
                results.append(stats)

        await asyncio.gather(*[process(fid) for fid in file_ids])

        return sorted(results, key=lambda x: x[method], reverse=True)[:limit]

    async def get_file_stats(self, file_id: str):
        trending = await self.calculate_trending_score(file_id)
        hotness = await self.calculate_hotness_score(file_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT download_count, first_download, last_download FROM files WHERE file_id = ?",
                (file_id,),
            )
            row = await cursor.fetchone()

        if not row:
            row = 0, None, None

        count, first, last = row

        return {
            "fileId": file_id,
            "downloadCount": count,
            "trendingScore": round(trending, 2),
            "hotnessScore": round(hotness, 2),
            "firstDownload": first,
            "lastDownload": last,
        }
