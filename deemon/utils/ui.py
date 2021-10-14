import os


TQDM_FORMAT = ":: {desc} {percentage:3.0f}%"


def get_progress_bar_size() -> int:
    try:
        screen_size = int(os.get_terminal_size().columns)
    except OSError:
        screen_size = 80

    dynamic_size = int(screen_size / 4)
    if dynamic_size > 30:
        return 30
    elif dynamic_size < 16:
        return 16
    else:
        return dynamic_size


def set_progress_bar_text(msg: str, max_length: int) -> str:
    max_cols = get_progress_bar_size()
    max_length += 11

    if max_length < max_cols:
        max_cols = max_length

    while len(msg) < max_cols:
        msg += " "
    while len(msg) > max_cols:
        msg = msg[:-1]
    msg += "..."
    return msg
