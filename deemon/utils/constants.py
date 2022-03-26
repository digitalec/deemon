RECORD_TYPES = {
    1: 'single',
    2: 'ep',
    4: 'album',
    8: 'unofficial',
    16: 'comps',
    32: 'feat',
}

BITRATES = {
    1: '128',
    3: '320',
    9: 'FLAC',
}

RELEASE_CHANNELS = [
    'beta',
    'stable',
]

SENSITIVE_KEYS = [
    'arl',
    'recipient_email',
    'smtp_server',
    'smtp_username',
    'smtp_password',
    'smtp_from_address',
    'token'
]

DEFAULT_CONFIG = {
    "app": {
        "check_update": 1,
        "debug_mode": False,
        "release_channel": "stable",
        "max_search_results": 5,
        "rollback_view_limit": 10,
        "prompt_duplicates": True,
        "prompt_no_matches": False,
        "max_release_age": 90,
        "fast_api": True,
        "away_mode": False,
    },
    "defaults": {
        "profile": 1,
        "download_path": "",
        "bitrate": "320",
        "record_types": [
            'album',
            'ep',
            'single'
        ],
    },
    "alerts": {
        "enabled": False,
        "recipient_email": "",
        "smtp_server": "",
        "smtp_port": 465,
        "smtp_username": "",
        "smtp_password": "",
        "smtp_from_address": "",
    },
    "deemix": {
        "path": "",
        "arl": "",
        "check_account_status": True
    },
    "plex": {
        "base_url": "",
        "token": "",
        "library": ""
    }
}