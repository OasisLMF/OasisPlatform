from channels.generic.websocket import AsyncJsonWebsocketConsumer


class TaskStatusConsumer(AsyncJsonWebsocketConsumer):
    groups = ['analysis_task_status']

    async def analysis_task_status_updated(self, event):
        await self.send_json(event)
