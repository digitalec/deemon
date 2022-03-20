ALLOWED_VALUES = {
    'bitrate': {"128": 1, "320": 3, "FLAC": 9},
    'alerts': [True, False],
    'record_types': ['album', 'ep', 'single', 'unofficial', 'comps', 'feat'],
    'release_channel': ['stable', 'beta']
}

SENSITIVE_KEYS = [
    'arl',
    'recipient_email',
    'smtp_server',
    'smtp_username',
    'smtp_password',
    'smtp_from_address',
    'token'
]