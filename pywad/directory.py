class DirectoryEntry:
    def __init__(self, owner, offset, size, name):
        self.owner = owner
        self.name = name.decode("ascii").rstrip("\0")
        self.size = size
        self.offset = offset

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}" / {self.size}>'
