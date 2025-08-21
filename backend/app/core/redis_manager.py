# backend/core/redis_manager.py
import redis.asyncio as redis
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional

class RedisManager:
    def __init__(self, redis_url="redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=False)
        
    async def cache_machine_status(self, machine_id: str, status: dict, ttl: int = 300):
        """Cache machine status for 5 minutes"""
        key = f"machine_status:{machine_id}"
        await self.redis.setex(key, ttl, json.dumps(status))
    
    async def get_machine_status(self, machine_id: str) -> Optional[dict]:
        """Get cached machine status"""
        key = f"machine_status:{machine_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def cache_anomaly_predictions(self, machine_id: str, predictions: list, ttl: int = 60):
        """Cache ML predictions for 1 minute"""
        key = f"predictions:{machine_id}"
        await self.redis.setex(key, ttl, pickle.dumps(predictions))
    
    async def get_anomaly_predictions(self, machine_id: str) -> Optional[list]:
        """Get cached predictions"""
        key = f"predictions:{machine_id}"
        data = await self.redis.get(key)
        return pickle.loads(data) if data else None
    
    async def publish_real_time_update(self, channel: str, data: dict):
        """Publish real-time updates via Redis pub/sub"""
        await self.redis.publish(channel, json.dumps(data))
    
    async def subscribe_to_updates(self, channels: list):
        """Subscribe to real-time updates"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub
