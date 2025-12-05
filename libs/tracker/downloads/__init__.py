# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

import math
from collections import defaultdict
from datetime import datetime, timedelta

from gdrive.utils import asyncio, run_async
from libs.time_cache import timed_cache


class DownloadTracker:
    def __init__(self):
        self.download_counts = defaultdict(int)
        self.first_download = {}
        self.last_download = {}
        self.download_history = defaultdict(list)

    def track_download(self, file_id: str, user_ip: str = None):
        self.download_counts[file_id] += 1
        timestamp = datetime.now()

        if file_id not in self.first_download:
            self.first_download[file_id] = timestamp

        self.last_download[file_id] = timestamp
        self.download_history[file_id].append({"timestamp": timestamp, "ip": user_ip})

    # Netflix/YouTube like trending algorithm (download only version):
    # Score = (Velocity * (Total Downloads ** 0.5)) * Recency *  Freshness Boost
    # Components:
    # 1. Velocity: Recent downloads per hour (last 24h)
    # 2. Total Downloads: Square root for diminishing returns
    # 3. Recency: Time decay based on last activity
    # 4. Freshness: Boost for newly downloaded content

    def _calculate_velocity(self, file_id: str, hours: int = 24) -> float:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_downloads = sum(
            1
            for d in self.download_history.get(file_id, [])
            if d["timestamp"] >= cutoff_time
        )

        return recent_downloads / hours if hours > 0 else 0.0

    def calculate_trending_score(self, file_id: str) -> float:
        if total_downloads := self.download_counts.get(file_id):
            # 1. Velocity Score (downloads per hour in last 24h)
            velocity_24h = self._calculate_velocity(file_id, hours=24)
            velocity_1h = self._calculate_velocity(file_id, hours=1)
            velocity_score = (velocity_24h * 1.0) + (velocity_1h * 5.0)

            # 2. Total downloads with diminishing returns
            popularity_score = math.sqrt(total_downloads)
        else:
            return 0.0

        # 3. Recency Weight (exponential decay, half life = 48 hours or 2 days)
        recency_weight = 0.0
        if last_dl := self.last_download.get(file_id):
            hours_since_activity = (datetime.now() - last_dl).total_seconds() / 3600
            recency_weight = math.exp(-0.693 * hours_since_activity / 48)

        # 4. Freshness Boost (newly popular content gets boost)
        freshness_boost = 1.0
        if first_dl := self.first_download.get(file_id):
            hours_since_first = (datetime.now() - first_dl).total_seconds() / 3600
            if hours_since_first < 72:  # lets give more boost in first 3 days
                freshness_boost = 2.0 - (hours_since_first / 72)  # 2.0 to 1.0

        return (
            (velocity_score * 3.0 + popularity_score) * recency_weight * freshness_boost
        )

    # Reddit/Hacker News like hotness algorithm (download only version)
    # Score = Downloads / ((Time Since First Download + 2) ** Gravity)
    # Gravity factor (higher = faster decay)
    def calculate_hotness_score(self, file_id: str, gravity: float = 1.5) -> float:
        if (downloads := self.download_counts.get(file_id)) and (
            first_dl := self.first_download.get(file_id)
        ):
            hours_old = (datetime.now() - first_dl).total_seconds() / 3600
            return (
                downloads / math.pow(hours_old + 2, gravity)
            ) * 1000  # x1000 fto scale up
        return 0.0

    @timed_cache(seconds=300)  # zyada compute nhi karwana h sir, bas aram karenge
    async def get_files_stats(self, limit: int = 10):
        file_scores = []
        tasks = [
            self.get_file_stats(file_id)
            for file_id in list(self.download_counts.keys())
        ]
        await asyncio.gather(*tasks)
        return sorted(file_scores, key=lambda x: x["score"], reverse=True)[:limit]

    @run_async
    def get_file_stats(self, file_id: str):
        return {
            "file_id": file_id,
            "download_count": self.download_counts.get(file_id, 0),
            "trending_score": round(self.calculate_trending_score(file_id), 2),
            "hotness_score": round(self.calculate_hotness_score(file_id), 2),
            "last_download": (
                self.last_download.get(file_id).isoformat()
                if file_id in self.last_download
                else None
            ),
            "first_download": (
                self.first_download.get(file_id).isoformat()
                if file_id in self.first_download
                else None
            ),
        }
