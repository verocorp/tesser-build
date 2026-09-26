package experimentcorpus

import "strings"

func application(options Options) string {
	body := inventoryStructured
	if options.Family == "transferring-funds" {
		body = fundsStructured
		if options.Variant == "scattered" {
			body = fundsScattered
		}
		body += fundsDispatch
	} else {
		if options.Variant == "scattered" {
			body = inventoryScattered
		}
		body += inventoryDispatch
	}
	rangeCheck := "1 <= value <= 1000"
	if options.Seed%2 != 0 {
		rangeCheck = "value >= 1 and value <= 1000"
	}
	return "import json\nimport sys\n\n\n" + strings.ReplaceAll(body, "VALID_RANGE", rangeCheck) + transport
}

const inventoryStructured = `class State:
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


`

const inventoryScattered = `class State:
    def __init__(self):
        self.stock = 10
        self.reserved = 0

    def status(self):
        return {"stock": self.stock, "reserved": self.reserved, "available": self.stock - self.reserved}

    def release(self, quantity):
        if quantity > self.reserved:
            return {"error": "insufficient_reserved"}
        self.reserved -= quantity
        return self.status()

    def restock(self, quantity):
        self.stock += quantity
        return self.status()


def reserve(state, quantity):
    if quantity > state.stock - state.reserved:
        return {"error": "insufficient_stock"}
    state.reserved += quantity
    return state.status()


def ship(state, quantity):
    if quantity > state.stock - state.reserved:
        return {"error": "insufficient_stock"}
    state.stock -= quantity
    return state.status()


`

const inventoryDispatch = `def dispatch(state, command):
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
    if type(value) is not int or not (VALID_RANGE):
        return {"error": "invalid_input"}
    if operation == "reserve":
        return reserve(state, value)
    if operation == "ship":
        return ship(state, value)
    if operation == "release":
        return state.release(value)
    return state.restock(value)


`

const fundsStructured = `class State:
    def __init__(self):
        self.accounts = {"amber": 100, "birch": 40}

    def balances(self):
        return dict(self.accounts)

    def move(self, source, destination, amount):
        if amount > self.accounts[source]:
            return {"error": "insufficient_funds"}
        self.accounts[source] -= amount
        self.accounts[destination] += amount
        return self.balances()


def transfer(state, source, destination, amount):
    return state.move(source, destination, amount)


def purchase(state, amount):
    return state.move("amber", "birch", amount)


`

const fundsScattered = `class State:
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


`

const fundsDispatch = `def dispatch(state, command):
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
    if type(value) is not int or not (VALID_RANGE):
        return {"error": "invalid_input"}
    if operation == "transfer":
        return transfer(state, source, destination, value)
    return purchase(state, value)


`

const transport = `def reject_constant(value):
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
`
