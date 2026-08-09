"""
Sanitized sample Instagram Messaging webhook payload fixtures from official Meta Graph API specifications.
"""

INSTAGRAM_TEXT_MESSAGE_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057200000,
            "messaging": [
                {
                    "sender": {"id": "ig_user_112233"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057200000,
                    "message": {
                        "mid": "aWdfbWlkX3RleHRfMTIzNDU",
                        "text": "Hi! Do you offer outdoor portrait shoots?",
                    },
                }
            ],
        }
    ],
}

INSTAGRAM_IMAGE_ATTACHMENT_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057205000,
            "messaging": [
                {
                    "sender": {"id": "ig_user_445566"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057205000,
                    "message": {
                        "mid": "aWdfbWlkX2ltYWdlXzk5ODg3Nw",
                        "text": "Here is the moodboard for reference",
                        "attachments": [
                            {
                                "type": "image",
                                "payload": {
                                    "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/sample_moodboard.jpg"
                                },
                            }
                        ],
                    },
                }
            ],
        }
    ],
}

INSTAGRAM_STORY_MENTION_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057210000,
            "messaging": [
                {
                    "sender": {"id": "ig_user_778899"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057210000,
                    "message": {
                        "mid": "aWdfbWlkX3N0b3J5XzExMjIzMw",
                        "attachments": [
                            {
                                "type": "story_mention",
                                "payload": {
                                    "url": "https://lookaside.fbsbx.com/ig_messaging_cdn/story_thumb.jpg"
                                },
                            }
                        ],
                    },
                }
            ],
        }
    ],
}

INSTAGRAM_QUICK_REPLY_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057215000,
            "messaging": [
                {
                    "sender": {"id": "ig_user_112233"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057215000,
                    "message": {
                        "mid": "aWdfbWlkX3F1aWNrXzQ0NTU2Ng",
                        "text": "Wedding Photography",
                        "quick_reply": {
                            "payload": "SELECTED_SERVICE_WEDDING",
                        },
                    },
                }
            ],
        }
    ],
}

INSTAGRAM_ECHO_MESSAGE_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057220000,
            "messaging": [
                {
                    "sender": {"id": "17841400000000001"},
                    "recipient": {"id": "ig_user_112233"},
                    "timestamp": 1723057220000,
                    "message": {
                        "mid": "aWdfbWlkX2VjaG9fOTk5",
                        "is_echo": True,
                        "text": "Thanks for contacting us! An admin will respond shortly.",
                    },
                }
            ],
        }
    ],
}

INSTAGRAM_MULTIPLE_MESSAGES_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057225000,
            "messaging": [
                {
                    "sender": {"id": "ig_user_multi_1"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057225000,
                    "message": {
                        "mid": "aWdfbWlkX211bHRpXzE",
                        "text": "Can I book tomorrow?",
                    },
                },
                {
                    "sender": {"id": "ig_user_multi_2"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057226000,
                    "message": {
                        "mid": "aWdfbWlkX211bHRpXzI",
                        "text": "What is the price for maternity shoot?",
                    },
                },
            ],
        }
    ],
}

INSTAGRAM_READ_RECEIPT_PAYLOAD = {
    "object": "instagram",
    "entry": [
        {
            "id": "17841400000000001",
            "time": 1723057230000,
            "messaging": [
                {
                    "sender": {"id": "ig_user_112233"},
                    "recipient": {"id": "17841400000000001"},
                    "timestamp": 1723057230000,
                    "read": {
                        "mid": "aWdfbWlkX3RleHRfMTIzNDU",
                        "watermark": 1723057230000,
                    },
                }
            ],
        }
    ],
}
