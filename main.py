# INIT STUFF

import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
import typing

def read_file(filename):
	f = open(filename, "r")
	t = f.read()
	f.close()
	return t

def bin_read_file(filename):
	f = open(filename, "rb")
	t = f.read()
	f.close()
	return t

def write_file(filename, content):
	f = open(filename, "w")
	f.write(content)
	f.close()

def read_json(filename):
	f = open(filename, "r")
	t = f.read()
	f.close()
	return json.loads(t)

def write_json(filename, content):
	f = open(filename, "w")
	f.write(json.dumps(content))
	f.close()

# GAME DEFINITIONS

class Player:
	def __init__(self, name):
		self.name = name
		self.money = 0
		self.inventory = {
			"apple": 1,
			"water": 1
		}
		self.trees = [
			Tree("default")
		]
	def info(self):
		for k in [*self.inventory.keys()]:
			if self.inventory[k] <= 0:
				del self.inventory[k]
		return json.dumps({
			"money": self.money,
			"inventory": self.inventory,
			"trees": [t.info() for t in self.trees]
		})
class Tree:
	def __init__(self, treeType):
		self.type = treeType
		self.grid = Grid(10, 10)
		starter = read_json(f"tree_types/{self.type}.json")["start"]
		self.grid.set_at([self.grid.get_width() // 2, self.grid.get_height() - 1], starter)
	def info(self):
		return self.grid.g
	def night(self):
		cmds = read_json(f"tree_types/{self.type}.json")["night"]
		executeCommandSet(self.grid, cmds)
class Grid:
	def __init__(self, width, height):
		self.g = [[None for ii in range(width)] for i in range(height)]
	def set_at(self, pos, value):
		self.g[pos[1]][pos[0]] = value
	def get_at(self, pos):
		return self.g[pos[1]][pos[0]]
	def get_width(self):
		return len(self.g[0])
	def get_height(self):
		return len(self.g)
	def inside(self, x, y):
		if x < 0: return False
		if y < 0: return False
		if x >= self.get_width(): return False
		if y >= self.get_height(): return False
		return True

def executeCommandSet(grid: Grid, cmds, pos: tuple[int, int] | None = (0, 0)) -> tuple[int, int] | None:
	for cmd in cmds:
		if cmd["type"] == "repeat": # Repeat {commands} {len} times
			for i in range(cmd["len"]):
				pos = executeCommandSet(grid, cmd["commands"], pos)
		elif cmd["type"] == "getblock":
			# Get a random {block} block
			filledblocks = [[x, y] for y in range(grid.get_height()) for x in range(grid.get_width()) if grid.get_at([x, y]) == cmd["block"]]
			if len(filledblocks): pos = random.choice(filledblocks) # type: ignore
			else: pos = None
		elif cmd["type"] == "growpos":
			# Go up and randomly left or right
			if pos == None:
				continue
			pos = (pos[0] + random.choice([-1, 0, 1]), pos[1] - 1)
		elif cmd["type"] == "set":
			# Fill the block with {block}
			if pos == None:
				continue
			if not grid.inside(*pos):
				continue
			if (not cmd["force"]) and grid.get_at(pos) != None:
				continue
			grid.set_at(pos, cmd["block"])
		elif cmd["type"] == "half":
			# 1/2 chance of doing {commands}
			if random.choice([True, False]):
				pos = executeCommandSet(grid, cmd["commands"], pos)
		elif cmd["type"] == "foreach":
			# For each {block} run {commands}
			filledblocks = [[x, y] for y in range(grid.get_height()) for x in range(grid.get_width()) if grid.get_at([x, y]) == cmd["block"]]
			for b in filledblocks:
				pos = executeCommandSet(grid, cmd["commands"], (*b,))
		elif cmd["type"] == "move":
			# Move by {x} {y}
			if pos == None:
				continue
			pos = (pos[0] + cmd["x"], pos[1] + cmd["y"])
	return pos

players = [
	Player("Jason")
]
trades: list[tuple[int, str | None, str, int, str | None]] = [
	(1, "leaves", "Sell 1 leaves for $1", 1, None),
	(10, "leaves", "Sell 10 leaves for $10", 10, None),
	(4, None, "Buy 1 water for $4", 1, "water"),
	(2, None, "Buy 1 apple for $2", 1, "apple"),
	(1, "wood", "Sell 1 wood for $4", 4, None)
]

# SERVER

hostName = "0.0.0.0"
serverPort = 8080

class HttpResponse(typing.TypedDict):
	status: int
	headers: dict[str, str]
	content: str | bytes

def get(path: str) -> HttpResponse:
	if path.split("?")[0] == "/":
		return {
			"status": 200,
			"headers": {
				"Content-Type": "text/html"
			},
			"content": read_file("index.html")
		}
	elif path.startswith("/userdata/"):
		username = path[10:]
		for p in players:
			if p.name == username:
				return {
					"status": 200,
					"headers": {
						"Content-Type": "text/json"
					},
					"content": p.info()
				}
		return {
			"status": 404,
			"headers": {
				"Content-Type": "text/html"
			},
			"content": f""
		}
	elif path == "/exchange":
		return {
			"status": 200,
			"headers": {
				"Content-Type": "text/json"
			},
			"content": json.dumps([x[2] for x in trades])
		}
	else: # 404 page
		return {
			"status": 404,
			"headers": {
				"Content-Type": "text/html"
			},
			"content": f""
		}

def post(path: str, body: bytes) -> HttpResponse:
	if path == "/night":
		# Check
		valid = True
		for p in players:
			if "apple" not in p.inventory.keys():
				valid = False
				break;
			if p.inventory["apple"] < 1:
				valid = False
				break;
			if "water" not in p.inventory.keys():
				valid = False
				break;
			if p.inventory["water"] < len(p.trees):
				valid = False
				break;
		# Night
		if valid:
			for p in players:
				p.inventory["apple"] -= 1
				p.inventory["water"] -= len(p.trees)
				for t in p.trees:
					t.night()
		return {
			"status": 200,
			"headers": {},
			"content": f""
		}
	elif path == "/take":
		bodydata = body.decode("UTF-8").split("\n")
		for p in players:
			if p.name == bodydata[0]:
				tree = p.trees[int(bodydata[1])]
				block: "str | None" = tree.grid.get_at([int(bodydata[2]), int(bodydata[3])])
				tree.grid.set_at([int(bodydata[2]), int(bodydata[3])], None)
				if block != None:
					if block not in p.inventory.keys(): p.inventory[block] = 0
					p.inventory[block] += 1
		return {
			"status": 200,
			"headers": {},
			"content": f""
		}
	elif path == "/destroy":
		bodydata = body.decode("UTF-8").split("\n")
		for p in players:
			if p.name == bodydata[0]:
				tree = p.trees[int(bodydata[1])]
				p.trees.remove(tree)
		return {
			"status": 200,
			"headers": {},
			"content": f""
		}
	elif path == "/exchange":
		bodydata = body.decode("UTF-8").split("\n")
		for p in players:
			if p.name == bodydata[0]:
				exc = trades[int(bodydata[1])]
				# Costs
				if exc[1] == None:
					if p.money < exc[0]:
						continue;
				else:
					if exc[1] not in p.inventory.keys():
						continue;
					if p.inventory[exc[1]] < exc[0]:
						continue;
				# Trade
				if exc[1] == None:
					p.money -= exc[0]
				else:
					p.inventory[exc[1]] -= exc[0]
				if exc[4] == None:
					p.money += exc[3]
				else:
					if exc[4] not in p.inventory.keys(): p.inventory[exc[4]] = 0
					p.inventory[exc[4]] += exc[3]
		return {
			"status": 200,
			"headers": {},
			"content": f""
		}
	else:
		return {
			"status": 404,
			"headers": {
				"Content-Type": "text/html"
			},
			"content": f""
		}

class MyServer(BaseHTTPRequestHandler):
	def do_GET(self):
		global running
		res = get(self.path)
		self.send_response(res["status"])
		for h in res["headers"]:
			self.send_header(h, res["headers"][h])
		self.end_headers()
		c = res["content"]
		cs = b""
		if type(c) == str: cs = c.encode("utf-8")
		elif type(c) == bytes: cs += c
		self.wfile.write(cs)
	def do_POST(self):
		res = post(self.path, self.rfile.read(int(self.headers["Content-Length"])))
		self.send_response(res["status"])
		for h in res["headers"]:
			self.send_header(h, res["headers"][h])
		self.end_headers()
		c = res["content"]
		cs = b""
		if type(c) == str: cs = c.encode("utf-8")
		elif type(c) == bytes: cs += c
		self.wfile.write(cs)
	def log_message(self, format: str, *args) -> None:
		return;
		if 400 <= int(args[1]) < 500:
			# Errored request!
			print(u"\u001b[31m", end="")
		print(args[0].split(" ")[0], "request to", args[0].split(" ")[1], "(status code:", args[1] + ")")
		print(u"\u001b[0m", end="")
		# don't output requests

if __name__ == "__main__":
	running = True
	webServer = HTTPServer((hostName, serverPort), MyServer)
	webServer.timeout = 1
	print("Server started http://%s:%s" % (hostName, serverPort))
	while running:
		try:
			webServer.handle_request()
		except KeyboardInterrupt:
			running = False
	webServer.server_close()
	print("Server stopped")
