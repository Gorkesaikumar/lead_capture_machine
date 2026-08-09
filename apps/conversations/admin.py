"""
Django admin integration for Conversation and Message models.
"""
from django.contrib import admin
from apps.conversations.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ("direction", "message_type", "text", "external_message_id", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "channel",
        "status",
        "unread_count",
        "last_message_at",
        "created_at",
    )
    list_filter = ("channel", "status", "unread_count", "created_at")
    search_fields = (
        "customer__display_name",
        "customer__primary_phone",
        "customer__email",
        "external_thread_id",
        "last_message_preview",
    )
    readonly_fields = ("created_at", "updated_at", "last_message_at")
    inlines = [MessageInline]
    ordering = ("-last_message_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "direction",
        "message_type",
        "text_preview",
        "external_message_id",
        "delivery_status",
        "created_at",
    )
    list_filter = ("direction", "message_type", "delivery_status", "created_at")
    search_fields = ("text", "external_message_id", "conversation__customer__display_name")
    readonly_fields = ("created_at", "updated_at")

    def text_preview(self, obj):
        return (obj.text[:50] + "...") if len(obj.text) > 50 else obj.text

    text_preview.short_description = "Content"
