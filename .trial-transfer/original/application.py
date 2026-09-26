import json
import sys


class FundsApplication:
    def __init__(self):
        self.balances = {"amber": 100, "birch": 40}

    def handle(self, request):
        if type(request) is not dict:
            return {"error": "invalid_input"}

        operation = request.get("op")
        if operation == "balances":
            if set(request) != {"op"}:
                return {"error": "invalid_input"}
            return dict(self.balances)

        if operation == "transfer":
            if set(request) != {"op", "from", "to", "amount"}:
                return {"error": "invalid_input"}
            source = request["from"]
            destination = request["to"]
            amount = request["amount"]
            if (type(source) is not str or source not in self.balances
                    or type(destination) is not str or destination not in self.balances
                    or source == destination or type(amount) is not int
                    or not 1 <= amount <= 1000):
                return {"error": "invalid_input"}
            return self._transfer(source, destination, amount)

        if operation == "purchase":
            if set(request) != {"op", "amount"}:
                return {"error": "invalid_input"}
            amount = request["amount"]
            if type(amount) is not int or not 1 <= amount <= 1000:
                return {"error": "invalid_input"}
            return self._transfer("amber", "birch", amount)

        return {"error": "invalid_input"}

    def _transfer(self, source, destination, amount):
        if self.balances[source] < amount:
            return {"error": "insufficient_funds"}
        self.balances[source] -= amount
        self.balances[destination] += amount
        return dict(self.balances)


def main():
    application = FundsApplication()
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = application.handle(request)
        except (json.JSONDecodeError, UnicodeDecodeError):
            response = {"error": "invalid_input"}
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
