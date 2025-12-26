class DetailedException(Exception):
    def __init__(self, details: dict):
        self.details = details
        super().__init__(str(details))


class FailedToFetchToken(DetailedException):
    pass


class FailedToFetchFileInfo(DetailedException):
    pass


class FailedToFetchFilesTree(DetailedException):
    pass


class FailedToFetchSearchResult(DetailedException):
    pass
