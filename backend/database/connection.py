"""
Database Manager with MongoDB & Resilient In-Memory Fallback
"""
import logging
from typing import Optional, Dict, Any, List
from backend.config.settings import settings

logger = logging.getLogger("backend.database")

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.is_connected = False
        # In-memory store for fallback mode
        self.in_memory_store: Dict[str, List[Dict[str, Any]]] = {
            "experiments": [],
            "network_metrics": [],
            "routing_decisions": [],
            "fault_events": [],
            "alerts": [],
        }

    async def connect(self):
        """Attempts to connect to MongoDB; gracefully falls back to in-memory store if unavailable."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self.client = AsyncIOMotorClient(
                settings.mongodb_uri,
                serverSelectionTimeoutMS=2000
            )
            # Test connection
            await self.client.admin.command('ping')
            self.db = self.client[settings.mongodb_database]
            self.is_connected = True
            logger.info(f"Connected to MongoDB at {settings.mongodb_uri}/{settings.mongodb_database}")
        except Exception as e:
            self.is_connected = False
            self.db = None
            logger.warning(f"MongoDB not reachable ({e}). Operating in resilient in-memory mode.")

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

    async def insert_one(self, collection: str, document: Dict[str, Any]):
        if self.is_connected and self.db is not None:
            await self.db[collection].insert_one(document)
        else:
            self.in_memory_store.setdefault(collection, []).append(document)

    async def find(self, collection: str, query: Dict[str, Any] = None, limit: int = 50) -> List[Dict[str, Any]]:
        query = query or {}
        if self.is_connected and self.db is not None:
            cursor = self.db[collection].find(query).limit(limit)
            return await cursor.to_list(length=limit)
        else:
            items = self.in_memory_store.get(collection, [])
            return items[-limit:]

db_manager = DatabaseManager()
