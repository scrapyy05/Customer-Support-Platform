import json
import asyncio
from typing import Dict, List
from fastapi import WebSocket
from app.core.redis import redis_client


class WebSocketManager:
    """
    Manages active WebSocket connections mapped by ticket_id.
    Listens to Redis Pub/Sub channels and broadcasts events to connected clients.
    """
    def __init__(self):
        # Maps ticket_id (str) to a list of connected WebSocket objects
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Keep track of active Redis pub/sub listener tasks so we don't duplicate them per ticket
        self.listeners: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, ticket_id: str):
        await websocket.accept()
        if ticket_id not in self.active_connections:
            self.active_connections[ticket_id] = []
        self.active_connections[ticket_id].append(websocket)

        # Start a Redis listener for this ticket if one doesn't exist
        if ticket_id not in self.listeners or self.listeners[ticket_id].done():
            task = asyncio.create_task(self._listen_to_redis(ticket_id))
            self.listeners[ticket_id] = task

    def disconnect(self, websocket: WebSocket, ticket_id: str):
        if ticket_id in self.active_connections:
            try:
                self.active_connections[ticket_id].remove(websocket)
            except ValueError:
                pass
            
            # If no more connections for this ticket, we could cancel the listener task
            if not self.active_connections[ticket_id]:
                if ticket_id in self.listeners:
                    self.listeners[ticket_id].cancel()
                    del self.listeners[ticket_id]
                del self.active_connections[ticket_id]

    async def broadcast_to_ticket(self, ticket_id: str, message_data: dict):
        """
        Publishes a message to the Redis channel for the ticket.
        """
        channel = f"ticket_updates:{ticket_id}"
        await redis_client.publish(channel, json.dumps(message_data))

    async def _listen_to_redis(self, ticket_id: str):
        """
        Background task that listens to a specific Redis Pub/Sub channel and routes 
        messages to all connected WebSockets for that ticket.
        """
        channel_name = f"ticket_updates:{ticket_id}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel_name)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    # Broadcast to all local websockets listening to this ticket
                    if ticket_id in self.active_connections:
                        dead_connections = []
                        for connection in self.active_connections[ticket_id]:
                            try:
                                await connection.send_text(data)
                            except Exception:
                                dead_connections.append(connection)
                        
                        # Cleanup dead connections
                        for dead in dead_connections:
                            self.disconnect(dead, ticket_id)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel_name)
            await pubsub.close()

# Singleton manager instance
ws_manager = WebSocketManager()
