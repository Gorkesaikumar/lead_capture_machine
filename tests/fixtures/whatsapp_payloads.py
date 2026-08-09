"""
Sanitized fixture payloads representing official Meta WhatsApp Cloud API webhooks.
Includes text messages, media, interactive button replies, and status updates (sent, delivered, read, failed).
"""

SAMPLE_WA_TEXT_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Anita Roy"},
                                "wa_id": "919876543210",
                            }
                        ],
                        "messages": [
                            {
                                "from": "919876543210",
                                "id": "wamid.HBgLMTIzNDU2Nzg5MA==",
                                "timestamp": "1723057200",
                                "type": "text",
                                "text": {
                                    "body": "Hi! Can you share pricing for a newborn shoot?",
                                },
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_WA_IMAGE_MESSAGE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Rahul Verma"},
                                "wa_id": "919811122233",
                            }
                        ],
                        "messages": [
                            {
                                "from": "919811122233",
                                "id": "wamid.HBgLMjIyMzMzNDQ0NQ==",
                                "timestamp": "1723057200",
                                "type": "image",
                                "image": {
                                    "id": "wa_media_id_555",
                                    "mime_type": "image/jpeg",
                                    "caption": "Looking for this theme!",
                                },
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_WA_BUTTON_REPLY_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "contacts": [
                            {
                                "profile": {"name": "Kavita S"},
                                "wa_id": "919899988877",
                            }
                        ],
                        "messages": [
                            {
                                "from": "919899988877",
                                "id": "wamid.HBgLMzg4ODc3NjY1NQ==",
                                "timestamp": "1723057200",
                                "type": "interactive",
                                "interactive": {
                                    "type": "button_reply",
                                    "button_reply": {
                                        "id": "btn_baby_shoot",
                                        "title": "Baby Photoshoot",
                                    },
                                },
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_WA_STATUS_SENT_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "statuses": [
                            {
                                "id": "wamid.OUTBOUND_TEST_101",
                                "status": "sent",
                                "timestamp": "1723057205",
                                "recipient_id": "919876543210",
                                "conversation": {
                                    "id": "conv_waba_101",
                                    "origin": {"type": "service"},
                                },
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_WA_STATUS_DELIVERED_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "statuses": [
                            {
                                "id": "wamid.OUTBOUND_TEST_101",
                                "status": "delivered",
                                "timestamp": "1723057210",
                                "recipient_id": "919876543210",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_WA_STATUS_READ_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "statuses": [
                            {
                                "id": "wamid.OUTBOUND_TEST_101",
                                "status": "read",
                                "timestamp": "1723057220",
                                "recipient_id": "919876543210",
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}

SAMPLE_WA_STATUS_FAILED_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "WABA_ID_98765",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550001111",
                            "phone_number_id": "109876543210",
                        },
                        "statuses": [
                            {
                                "id": "wamid.OUTBOUND_TEST_FAILED_202",
                                "status": "failed",
                                "timestamp": "1723057230",
                                "recipient_id": "919876543210",
                                "errors": [
                                    {
                                        "code": 131026,
                                        "title": "Message undeliverable",
                                        "message": "Recipient phone is out of service",
                                    }
                                ],
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}
