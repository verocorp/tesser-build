"""The AST tool CANNOT catch this either: the annotation text is `Tags`, not
`dict` -- only resolving the alias reveals it's a dict."""
from dataclasses import dataclass

Tags = dict[str, str]


@dataclass(frozen=True)
class Labeled:
    tags: Tags  # alias to dict -- DDD002 (non-literal alias case)


x = Labeled(tags={"a": "b"})  # valid construction call
