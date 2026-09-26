import json
import subprocess
import sys
import unittest

from application import FundsApplication


class FundsApplicationTests(unittest.TestCase):
    def setUp(self):
        self.app = FundsApplication()

    def test_initial_balances_exact(self):
        self.assertEqual(self.app.handle({"op": "balances"}), {"amber": 100, "birch": 40})

    def test_transfer_both_directions_preserves_conservation(self):
        initial_total = sum(self.app.balances.values())
        self.assertEqual(self.app.handle({"op": "transfer", "from": "amber", "to": "birch", "amount": 30}), {"amber": 70, "birch": 70})
        self.assertEqual(sum(self.app.balances.values()), initial_total)
        self.assertEqual(self.app.handle({"op": "transfer", "from": "birch", "to": "amber", "amount": 50}), {"amber": 120, "birch": 20})
        self.assertEqual(sum(self.app.balances.values()), initial_total)

    def test_purchase_is_transfer_from_amber_to_birch(self):
        self.assertEqual(self.app.handle({"op": "purchase", "amount": 25}), {"amber": 75, "birch": 65})

    def test_insufficient_funds_does_not_mutate(self):
        before = dict(self.app.balances)
        self.assertEqual(self.app.handle({"op": "transfer", "from": "birch", "to": "amber", "amount": 41}), {"error": "insufficient_funds"})
        self.assertEqual(self.app.balances, before)
        self.assertEqual(self.app.handle({"op": "purchase", "amount": 101}), {"error": "insufficient_funds"})
        self.assertEqual(self.app.balances, before)

    def test_invalid_requests(self):
        invalid = [
            None, [], "balances", {},
            {"op": "balances", "amount": 1},
            {"op": "transfer", "from": "amber", "to": "amber", "amount": 1},
            {"op": "transfer", "from": "amber", "to": "cedar", "amount": 1},
            {"op": "transfer", "from": "amber", "to": "birch", "amount": True},
            {"op": "transfer", "from": "amber", "to": "birch", "amount": 0},
            {"op": "transfer", "from": "amber", "to": "birch", "amount": 1001},
            {"op": "purchase", "amount": 1, "from": "amber"},
            {"op": "purchase", "amount": 1.0},
            {"op": "purchase", "amount": -1},
            {"op": "wat"},
        ]
        before = dict(self.app.balances)
        for request in invalid:
            with self.subTest(request=request):
                self.assertEqual(self.app.handle(request), {"error": "invalid_input"})
                self.assertEqual(self.app.balances, before)

    def test_validation_precedes_insufficient_funds_state_check(self):
        request = {"op": "transfer", "from": "birch", "to": "amber", "amount": 1001}
        self.assertEqual(self.app.handle(request), {"error": "invalid_input"})

    def test_json_lines_process_state_persists(self):
        app_path = __file__.replace("test_application.py", "application.py")
        run = subprocess.run(
            [sys.executable, app_path],
            input='{"op":"purchase","amount":10}\n{"op":"balances"}\n',
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(run.stdout.splitlines(), [
            '{"amber":90,"birch":50}',
            '{"amber":90,"birch":50}',
        ])
        self.assertEqual(run.stderr, "")

    def test_malformed_json_line_does_not_stop_stream(self):
        app_path = __file__.replace("test_application.py", "application.py")
        run = subprocess.run(
            [sys.executable, app_path],
            input='not json\n{"op":"balances"}\n',
            text=True, capture_output=True, check=True,
        )
        self.assertEqual(run.stdout.splitlines(), [
            '{"error":"invalid_input"}',
            '{"amber":100,"birch":40}',
        ])


if __name__ == "__main__":
    unittest.main()
