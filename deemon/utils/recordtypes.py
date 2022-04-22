from .constants import RECORD_TYPES


def get_record_type_index(user_types: list):
    """
    Determines number based on user specified record types
    by adding each ID (key) from RECORD_TYPES
    """
    if "all" in user_types:
        user_types += "album", "single", "ep"
        user_types.remove("all")

    record_type_index = 0
    for key, value in RECORD_TYPES.items():
        for ut in user_types:
            if ut == value:
                record_type_index += key
    return record_type_index


def compare_record_type_index(allowed_rti: int, release_rti: int):
    """ Convert Record Type Index to list of string record types for comparison"""

    allowed_types = get_record_type_str(allowed_rti)
    release_types = get_record_type_str(release_rti)

    if all(elem in allowed_types for elem in release_types):
        return True


def convert_index_to_binary(i):
    """
    Converts record_type_index to binary format and
    returns a comma separated list.

    E.g. 7 -> [0, 0, 0, 1, 1, 1]
    """
    b = format(i, "006b")
    return [int(x) for x in list(b)]


def convert_binary_to_record_types(binary_index):
    """
    Converts binary list to list of str record_types

    E.g. [0, 0, 0, 1, 1, 1] -> ['album', 'ep', 'single']
    """
    active_record_types = []
    max_binary = 32
    for t in binary_index:
        if t:
            active_record_types.append(RECORD_TYPES[max_binary])
        if max_binary > 1:
            max_binary = max_binary / 2
        else:
            max_binary = 0
    return active_record_types


def get_record_type_str(rti: int):
    """
    Accepts a Record Type Index (RTI) and returns a list
    of strings containg record type names
    """
    # RTI must be between 1 and 63
    if rti not in range(1, 63):
        return
    rt_binary = convert_index_to_binary(rti)
    return convert_binary_to_record_types(rt_binary)
