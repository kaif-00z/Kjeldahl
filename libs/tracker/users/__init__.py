# Google-Drive-Mirror - Mirror/Indexer of Gdrive with FastAPI
# Copyright (C) 2025 kaif-00z
#
# This file is a part of < https://github.com/kaif-00z/Google-Drive-Mirror/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/kaif-00z/Google-Drive-Mirror/blob/main/LICENSE>.

# if you are using this following code then don't forgot to give proper
# credit to t.me/kAiF_00z (github.com/kaif-00z)

from datetime import datetime, timedelta
import aiosqlite

class Activities:
    BROWSE = "browsing"
    DL = "download"
    SRCH = "search"

class UserTracker:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_ip TEXT PRIMARY KEY,
                    requests_count INTEGER DEFAULT 0,
                    downloads_count INTEGER DEFAULT 0,
                    first_access TEXT,
                    last_access TEXT,
                    is_flagged INTEGER DEFAULT 0
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_ip TEXT,
                    activity_type TEXT,
                    file_name TEXT,
                    details TEXT,
                    bandwidth INTEGER DEFAULT 0,
                    timestamp TEXT
                )
                """
            )
            await db.commit()

    async def is_suspicious(self, user_ip: str) -> bool:
        min = (datetime.now() - timedelta(minutes=1)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM activity_logs WHERE user_ip = ? AND timestamp > ?",
                (user_ip, min)
            )
            return (await cursor.fetchone())[0] > 60

    async def track_user(self, user_ip: str, activity_type: str = Activities.BROWSE, file_name: str = None, details: str = None) -> int:
        timestamp = datetime.now().isoformat()
        is_download = int(activity_type == Activities.DL)
        is_suspicious = int(await self.is_suspicious(user_ip))

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO activity_logs (user_ip, activity_type, file_name, details, bandwidth, timestamp)
                VALUES (?, ?, ?, ?, 0, ?)
                """,
                (user_ip, activity_type, file_name, details, timestamp),
            )
            activity_id = cursor.lastrowid

            await db.execute(
                """
                INSERT INTO users (user_ip, requests_count, downloads_count, first_access, last_access, is_flagged)
                VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(user_ip) DO UPDATE SET
                    requests_count = requests_count + 1,
                    downloads_count = downloads_count + excluded.downloads_count,
                    last_access = excluded.last_access,
                    is_flagged = MAX(users.is_flagged, excluded.is_flagged)
                """,
                (user_ip, is_download, timestamp, timestamp, is_suspicious),
            )

            await db.commit()
            return activity_id

    async def add_bandwidth_usage(self, activity_id: int, bytes_used: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE activity_logs
                SET bandwidth = bandwidth + ?
                WHERE id = ?
                """,
                (bytes_used, activity_id),
            )
            await db.commit()

    async def calculate_bandwidth(self, user_ip: str = None) -> int:
        bandwidth_stats = {}
        now = datetime.now()
        async with aiosqlite.connect(self.db_path) as db:
            periods = {
                "hour": timedelta(hours=1),
                "day": timedelta(days=1),
                "week": timedelta(weeks=1),
                "month": timedelta(days=30),
                "year": timedelta(days=365)
            }
            
            for name, delta in periods.items():
                cutoff = (now - delta).isoformat()
                if user_ip is None:
                    bw_cursor = await db.execute(
                        "SELECT SUM(bandwidth) FROM activity_logs WHERE timestamp > ?",
                        (cutoff,)
                    )
                else:
                    bw_cursor = await db.execute(
                        "SELECT SUM(bandwidth) FROM activity_logs WHERE user_ip = ? AND timestamp > ?",
                        (user_ip, cutoff)
                    )
                bandwidth_stats[name] = int((await bw_cursor.fetchone())[0] or 0)
            
            bandwidth_stats["total"] = sum(bandwidth_stats.values())
            return bandwidth_stats

    async def get_user_info(self, user_ip: str) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_ip, requests_count, downloads_count, bandwidth_usage, first_access, last_access, is_flagged FROM users WHERE user_ip = ?",
                (user_ip,),
            )
            if row := await cursor.fetchone():
                return {
                    "user_ip": row[0],
                    "requests_count": row[1],
                    "downloads_count": row[2],
                    "bandwidth_usage": await self.calculate_bandwidth(user_ip),
                    "first_access": row[4],
                    "last_access": row[5],
                    "is_flagged": bool(row[6]),
                }
            return {}
        
    async def is_flagged_user(self, user_ip: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT is_flagged FROM users WHERE user_ip = ?",
                (user_ip,),
            )
            row = await cursor.fetchone()
            return bool(row[0]) if row else False
        
    async def get_latest_activities(self, limit: int = 100) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_ip, activity_type, file_name, details, bandwidth, timestamp FROM activity_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            if rows := await cursor.fetchall():
                return [
                    {
                        "user_ip": row[0],
                        "activity_type": row[1],
                        "file_name": row[2],
                        "details": row[3],
                        "bandwidth": row[4],
                        "timestamp": row[5],
                    }
                    for row in rows
                ]
            return []
        
    async def get_latest_activities_by_user(self, user_ip: str, limit: int = 100) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_ip, activity_type, file_name, details, bandwidth, timestamp FROM activity_logs WHERE user_ip = ? ORDER BY timestamp DESC LIMIT ?",
                (user_ip, limit),
            )
            if rows := await cursor.fetchall():
                return [
                    {
                        "user_ip": row[0],
                        "activity_type": row[1],
                        "file_name": row[2],
                        "details": row[3],
                        "bandwidth": row[4],
                        "timestamp": row[5],
                    }
                    for row in rows
                ]
            return []

    async def get_latest_activities_by_type(self, activity_type: str, limit: int = 100) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_ip, activity_type, file_name, details, bandwidth, timestamp FROM activity_logs WHERE activity_type = ? ORDER BY timestamp DESC LIMIT ?",
                (activity_type, limit),
            )
            if rows := await cursor.fetchall():
                return [
                    {
                        "user_ip": row[0],
                        "activity_type": row[1],
                        "file_name": row[2],
                        "details": row[3],
                        "bandwidth": row[4],
                        "timestamp": row[5],
                    }
                    for row in rows
                ]
            return []
        
    async def total_downloads_recorded(self, days: int = None, hours: int = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if days is not None:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor = await db.execute(
                    "SELECT SUM(downloads_count) FROM users WHERE last_access >= ?",
                    (cutoff,)
                )
            elif hours is not None:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                cursor = await db.execute(
                    "SELECT SUM(downloads_count) FROM users WHERE last_access >= ?",
                    (cutoff,)
                )
            else:
                cursor = await db.execute(
                    "SELECT SUM(downloads_count) FROM users"
                )
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        
    async def total_requests_recorded(self, days: int = None, hours: int = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if days is not None:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor = await db.execute(
                    "SELECT SUM(requests_count) FROM users WHERE last_access >= ?",
                    (cutoff,)
                )
            elif hours is not None:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                cursor = await db.execute(
                    "SELECT SUM(requests_count) FROM users WHERE last_access >= ?",
                    (cutoff,)
                )
            else:
                cursor = await db.execute(
                    "SELECT SUM(requests_count) FROM users"
                )
            row = await cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        
    async def unique_users_count(self, days: int = None, hours: int = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if days is not None:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE first_access >= ?",
                    (cutoff,)
                )
            elif hours is not None:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE first_access >= ?",
                    (cutoff,)
                )
            else:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users"
                )
            row = await cursor.fetchone()
            return row[0] if row else 0
        
    async def flagged_users_count(self, days: int = None, hours: int = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            if days is not None:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE is_flagged = 1 AND last_access >= ?",
                    (cutoff,)
                )
            elif hours is not None:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE is_flagged = 1 AND last_access >= ?",
                    (cutoff,)
                )
            else:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE is_flagged = 1"
                )
            row = await cursor.fetchone()
            return row[0] if row else 0
        
    async def flagged_users_list(self, days: int = None, hours: int = None, limit: int = 100) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            if days is not None:
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                cursor = await db.execute(
                    "SELECT user_ip, requests_count, downloads_count, first_access, last_access FROM users WHERE is_flagged = 1 AND last_access >= ? ORDER BY last_access DESC LIMIT ?",
                    (cutoff, limit),
                )
            elif hours is not None:
                cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
                cursor = await db.execute(
                    "SELECT user_ip, requests_count, downloads_count, first_access, last_access FROM users WHERE is_flagged = 1 AND last_access >= ? ORDER BY last_access DESC LIMIT ?",
                    (cutoff, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT user_ip, requests_count, downloads_count, first_access, last_access FROM users WHERE is_flagged = 1 ORDER BY last_access DESC LIMIT ?",
                    (limit,),
                )
            if rows := await cursor.fetchall():
                return [
                    {
                        "user_ip": row[0],
                        "requests_count": row[1],
                        "downloads_count": row[2],
                        "first_access": row[3],
                        "last_access": row[4],
                    }
                    for row in rows
                ]
            return []