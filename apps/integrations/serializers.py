"""
Serializers for Integrations module.
"""
from rest_framework import serializers


class OutboundMessageSerializer(serializers.Serializer):
    """
    Serializer for sending outbound messages to Instagram or WhatsApp.
    """

    channel = serializers.ChoiceField(choices=["INSTAGRAM", "WHATSAPP"])
    recipient_id = serializers.CharField(max_length=255)
    text = serializers.CharField(required=False, allow_blank=True)
    media_url = serializers.URLField(required=False, allow_blank=True)
    media_type = serializers.ChoiceField(
        choices=["IMAGE", "VIDEO", "AUDIO", "DOCUMENT"], default="IMAGE", required=False
    )
    caption = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get("text") and not attrs.get("media_url"):
            raise serializers.ValidationError("Either text or media_url must be provided.")
        return attrs


class WebhookResponseSerializer(serializers.Serializer):
    """
    Serializer describing webhook ingestion results.
    """

    success = serializers.BooleanField()
    messages_processed = serializers.IntegerField(default=0)
    new_messages_created = serializers.IntegerField(default=0)
    leads_created = serializers.IntegerField(default=0)
    notes = serializers.CharField(required=False)
