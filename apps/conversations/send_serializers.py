from rest_framework import serializers


class TemplateSerializer(serializers.Serializer):
    name = serializers.RegexField(r"^[a-z0-9_]+$", max_length=512)
    language = serializers.RegexField(r"^[a-z]{2,3}(_[A-Z]{2})?$", max_length=16)
    components = serializers.ListField(child=serializers.DictField(), required=False, max_length=20)


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    media_url = serializers.URLField(required=False, max_length=2048)
    media_type = serializers.ChoiceField(choices=["IMAGE", "VIDEO", "AUDIO", "DOCUMENT"], required=False)
    caption = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    template = TemplateSerializer(required=False)
    request_id = serializers.CharField(max_length=128, required=False)

    def validate(self, data):
        if sum(bool(data.get(k)) for k in ("text", "media_url", "template")) != 1:
            raise serializers.ValidationError("Provide exactly one of text, media_url, or template.")
        if data.get("media_url") and (not data["media_url"].startswith("https://") or not data.get("media_type")):
            raise serializers.ValidationError("Media requires an HTTPS URL and media_type.")
        return data
