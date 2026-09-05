from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task(name="apps.conversations.dispatch_message", acks_late=True)
def dispatch_message_task(message_id):
    from .outbound import dispatch_message
    message = dispatch_message(message_id)
    return {"message_id": str(message.pk), "status": message.delivery_status}


@shared_task(name="apps.conversations.drain_outbox")
def drain_outbox():
    from .models import Message
    from .outbound import enqueue_dispatch
    stale = timezone.now()-timedelta(minutes=10)
    Message.objects.filter(delivery_status="SENDING", updated_at__lt=stale).update(
        delivery_status="FAILED", error_code="delivery_unconfirmed",
        error_message="Worker interrupted; check channel activity before resending.",
    )
    for message_id in Message.objects.filter(delivery_status="QUEUED").values_list("pk", flat=True)[:100]:
        enqueue_dispatch(str(message_id))
