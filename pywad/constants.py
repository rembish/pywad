from re import compile as re_compile

HEADER_FORMAT = "<4sII"
DIRECTORY_ENTRY_FORMAT = "<II8s"

DOOM1_MAP_NAME_REGEX = re_compile(r'^E(?P<episode>[0-9])M(?P<number>[0-9])$')
DOOM2_MAP_NAME_REGEX = re_compile(r'^MAP(?P<number>[0-9]{2})$')
