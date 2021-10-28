"""
Models used by the autoscaler.
"""

from typing import TypedDict, List


class SocketQueueEntry(TypedDict):
    """
    Websocket message - the /content/queue object.
    Type describing the used parts of the queue info
    """
    name: str
    pending_count: int
    worker_count: int
    queued_count: int
    running_count: int


class QueueStatusTask(TypedDict):
    """
    Websocket message - the /content/queue/analyses/analysis/sub_task_statuses object.
    """
    queue_name: str


class QueueStatusAnalysis(TypedDict):
    """
    Websocket message - the /content/queue/analyses/analysis/ object.
    """
    id: int
    lookup_chunks: int
    analysis_chunks: int
    sub_task_count: int
    sub_task_statuses: List[QueueStatusTask]


class QueueStatusAnalysesEntry(TypedDict):
    """
    Websocket message - the /content/queue/analyses object
    """
    analysis: List[QueueStatusAnalysis]


class QueueStatusContentEntry(TypedDict):
    """
    Websocket message - the /content/ object
    """
    queue: SocketQueueEntry
    analyses: List[QueueStatusAnalysesEntry]


class QueueStatusSocketMessage(TypedDict):
    """
    Websocket message - the root object
    """
    content: List[QueueStatusContentEntry]


class RunningAnalysis(TypedDict):
    """
    Used to store analysis information from the websocket message.
    """
    id: int
    tasks: int
    queue_names: List[str]


class ModelState(TypedDict):
    """
    Used in the model states dict to store information about each models current states. For now number of tasks
    and analyses for each model.
    """
    tasks: int
    analyses: int
