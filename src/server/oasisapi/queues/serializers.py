from rest_framework import serializers


class QueueSerializer(serializers.Serializer):
    name = serializers.CharField()
    worker_count = serializers.IntegerField()
    queued_count = serializers.IntegerField()
    running_count = serializers.IntegerField()
