import json
import sys


class State:
    def __init__(self):
        self.accounts = {"amber": 100, "birch": 40}

    def balances(self):
        return dict(self.accounts)


def transfer(state, source, destination, amount):
    if amount > state.accounts[source]:
        return {"error": "insufficient_funds"}
    state.accounts[source] -= amount
    state.accounts[destination] += amount
    return state.balances()


def purchase(state, amount):
    if amount > state.accounts["amber"]:
        return {"error": "insufficient_funds"}
    state.accounts["amber"] -= amount
    state.accounts["birch"] += amount
    return state.balances()


def dispatch(state, command):
    if type(command) is not dict or type(command.get("op")) is not str:
        return {"error": "invalid_input"}
    operation = command["op"]
    if operation == "balances":
        if set(command) != {"op"}:
            return {"error": "invalid_input"}
        return state.balances()
    if operation == "transfer":
        if set(command) != {"op", "from", "to", "amount"}:
            return {"error": "invalid_input"}
        source, destination = command["from"], command["to"]
        if type(source) is not str or type(destination) is not str:
            return {"error": "invalid_input"}
        if source not in {"amber", "birch"} or destination not in {"amber", "birch"} or source == destination:
            return {"error": "invalid_input"}
    elif operation == "purchase":
        if set(command) != {"op", "amount"}:
            return {"error": "invalid_input"}
    else:
        return {"error": "invalid_input"}
    value = command["amount"]
    if type(value) is not int or not (value >= 1 and value <= 1000):
        return {"error": "invalid_input"}
    if operation == "transfer":
        return transfer(state, source, destination, value)
    return purchase(state, value)


def reject_constant(value):
    raise ValueError(value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(key)
        result[key] = value
    return result


def main():
    state = State()
    for line in sys.stdin:
        try:
            command = json.loads(line, parse_constant=reject_constant, object_pairs_hook=unique_object)
        except ValueError:
            result = {"error": "invalid_input"}
        else:
            result = dispatch(state, command)
        print(json.dumps(result, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
