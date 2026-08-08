import tesser.context as ts


class DigestRequest(ts.Request):

    def __init__(self, text: str) -> None:
        self.text = text


class DigestResponse(ts.Response):

    def __init__(self, headline: str) -> None:
        self.headline = headline
