import tesser.component as ts

import tesserinspect.adapters.repositories as repositories
import tesserinspect.application as application
import tesserinspect.client as client


class Spec(ts.Spec):
    def __init__(self) -> None:
        return None


class Config(ts.Config):
    def __init__(self, spec: Spec) -> None:
        return None


class Inspection(ts.Component):
    def __init__(self, config: Config) -> None:
        self.client: client.InspectionClient = application.InspectionService(
            repositories.GitCheckoutReader()
        )

    def close(self) -> None:
        return None
