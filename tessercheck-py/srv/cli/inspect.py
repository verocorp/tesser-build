import tesser.srv as ts

import app
import protocol
import tesserinspect.adapters.handlers as tesserinspect_handlers


class InspectHost(ts.Host):
    def run(self, argv: list[str]) -> int:
        inspection_app = app.InspectionApp()
        try:
            inspection_handler = tesserinspect_handlers.InspectionHandler(
                inspection_app.inspection.client
            )
            cli_response = inspection_handler.inspect(
                protocol.CliRequest(args=tuple(argv))
            )
            print(cli_response.stdout)
            return cli_response.exit_code
        finally:
            inspection_app.close()


if __name__ == "__main__":
    ts.main(InspectHost().run)
