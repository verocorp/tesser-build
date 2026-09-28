import tesser.app as ts

import tesserinspect.component as tesserinspect_component


class InspectionApp(ts.App):
    def __init__(self) -> None:
        self.inspection = tesserinspect_component.Inspection(
            tesserinspect_component.Config(tesserinspect_component.Spec())
        )

    def close(self) -> None:
        self.inspection.close()
