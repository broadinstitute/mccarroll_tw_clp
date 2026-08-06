class YamlException(Exception):
    def __init__(self, message: str, cause: Exception = None):
        super().__init__(message)
        if cause is not None:
            self.__cause__ = cause
