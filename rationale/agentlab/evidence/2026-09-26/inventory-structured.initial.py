import json
import sys


class State:
    def __init__(self):
        self.stock = 10
        self.reserved = 0

    def status(self):
        return {"stock": self.stock, "reserved": self.reserved, "available": self.stock - self.reserved}

    def allocate(self, quantity, reserve):
        if quantity > self.stock - self.reserved:
            return {"error": "insufficient_stock"}
        if reserve:
            self.reserved += quantity
        else:
            self.stock -= quantity
        return self.status()

    def release(self, quantity):
        if quantity > self.reserved:
            return {"error": "insufficient_reserved"}
        self.reserved -= quantity
        return self.status()

    def restock(self, quantity):
        self.stock += quantity
        return self.status()


def reserve(state, quantity):
    return state.allocate(quantity, True)


def ship(state, quantity):
    return state.allocate(quantity, False)


def dispatch(state, command):
    if type(command) is not dict or type(command.get("op")) is not str:
        return {"error": "invalid_input"}
    operation = command["op"]
    if operation == "status":
        if set(command) != {"op"}:
            return {"error": "invalid_input"}
        return state.status()
    if operation not in {"reserve", "ship", "release", "restock"} or set(command) != {"op", "quantity"}:
        return {"error": "invalid_input"}
    value = command["quantity"]
    if type(value) is not int or not (value >= 1 and value <= 1000):
        return {"error": "invalid_input"}
    if operation == "reserve":
        return reserve(state, value)
    if operation == "ship":
        return ship(state, value)
    if operation == "release":
        return state.release(value)
    return state.restock(value)


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
