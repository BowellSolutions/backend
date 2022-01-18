"""
author: Adam Lisichin

description: Exports DashboardConsumer which handles websocket message in ws/users/<user_code> routes.
"""
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncJsonWebsocketConsumer):
    """Websocket consumer used for sending real time data."""
    room_code: str
    user_group_name: str

    commands = {}

    async def connect(self):
        # do not allow unauthorized users
        if not (current_user := self.scope.get('user')) or current_user.is_anonymous:
            logger.warning(f"Dashboard Consumer - Unauthorized user tried to connect")
            return

        self.user_group_name = f"user-{current_user.id}"

        # create group with single user
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        # send greeting to user after accepting incoming socket (example - remove later)
        await self.channel_layer.group_send(
            group=self.user_group_name,
            message={"type": "hello", "message": "Connection with real-time analysis service established!"}
        )

    async def receive_json(self, content, **kwargs):
        command = content.get('type')

        if settings.DEBUG:
            logger.debug("WS RECEIVE", content)

        try:
            await self.channel_layer.group_send(
                group=self.user_group_name,
                message={'type': self.commands[command]}
            )
        except KeyError:
            logger.warning(f"WS INVALID COMMAND: {command}")

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(
                group=self.user_group_name,
                channel=self.channel_name
            )
        except AttributeError as e:
            # if consumer has no attribute user_group_name, then there is nothing to discard
            logger.warning("Dashboard Consumer - error while disconnecting")
            logger.warning(e)

    async def hello(self, event):
        message = event.get("message")
        await self.send_json({"type": "hello", "message": message, "timestamp": timezone.now().isoformat()})

    async def notify(self, event):
        message = event.get("message")
        await self.send_json({"type": "notify", "message": message, "timestamp": timezone.now().isoformat()})

    async def update_examination(self, event):
        examination = event.get("payload")
        message = event.get("message")
        await self.send_json(
            {
                "type": "update_examination", "payload": examination,
                "message": message, "timestamp": timezone.now().isoformat()
            }
        )
