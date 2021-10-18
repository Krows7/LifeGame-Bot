import random
import discord
import config
import logging
import sys
import time
from datetime import datetime
from unittest.mock import Mock

get_config = lambda x, d: getattr(config, x) if hasattr(config, x) else d
error = lambda e: logger.exception('Exception Caught: ', exc_info=(e))

formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s]: %(message)s')

handler = logging.FileHandler(filename='logs/' + datetime.now().strftime('%Y-%m-%d %H.%M.%S') + '.log', encoding='utf-8', mode='w')
handler.setFormatter(formatter)

handler_current = logging.FileHandler(filename='logs/latest.log', encoding='utf-8', mode='w')
handler_current.setFormatter(formatter)

logger = logging.getLogger('life-bot')
logger.setLevel(get_config('LOG_LEVEL', 'INFO'))
logger.addHandler(handler)
logger.addHandler(handler_current)

sys.excepthook = lambda x, y, z: logger.error(msg='Exception Caught: ', exc_info=(x, y, z))

class LifeGame:

	def __init__(self, x, y):
		self.x = x
		self.y = y
		self.cx = 0
		self.cy = 0
		self.field = LifeGame.create_field(x, y)
		self.running = False

	@staticmethod
	def create_field(x, y):
		return [[0] * y for i in range(x)]

	@staticmethod
	def clamp(value, end):
		return value % end

	def neighbour_count(self, x, y):
		r = 0
		for i in range(- 1, 2):
			for j in range(- 1, 2):
				if i == j == 0: continue
				r += self.field[LifeGame.clamp(x + i, self.x)][LifeGame.clamp(y + j, self.y)]
		return r

	def step(self):
		field = LifeGame.create_field(self.x, self.y)
		for y in range(self.y):
			for x in range(self.x):
				neigh = self.neighbour_count(x, y)
				field[x][y] = 1 if neigh == 3 or (neigh == 2 and self.field[x][y]) else 0
		self.field = field


class Client(discord.Client):

	BLACK_SQUARE = ':black_large_square:'
	WHITE_SQUARE = ':white_large_square:'
	YELLOW_SQUARE = ':yellow_square:'

	HELP_TEMPLATE = '''
	'Life-Game' bot help:
	#start <width> <height> [has_borders=False] — starts new game in new message. Type #help-start for more details
	#help / #info — shows 'help' message
	#exit — shutdowns bot.
	'''

	HELP_PLAY_TEMPLATE = '''
	Creates new game instance in the following message.
	<width> — integer argument of field width
	<height> — integer argument of field height
	[has_borders] — optional argument whether field is restricted or borderless (by default is borderless)
	------------
	Field has restrictions of size due to Discord limitations (Width x Height position is unimportant):
	10 x 9
	9 x 12
	8 x 10
	7 x 14
	6 x 16
	5 x 20
	.
	.
	.
	'''

	REACTIONS = {
		'ARROW_LEFT': '⬅️',
		'ARROW_RIGHT': '➡️',
		'ARROW_UP': '⬆️',
		'ARROW_DOWN': '⬇️',
		'PICK': '⏏️',
		'REFRESH': '🔁',
		'START': '✅',
		'RANDOMIZE': '🎲',
	}

	async def on_ready(self):
		logger.info(f'Logged on as {self.user}.')

	async def update_field(self):
		await self.game_msg.edit(content=Client.get_field_msg(self.game))
		time.sleep(1)

	async def init_game(self, com, msg):
		logger.debug('Init game...')
		x, y = map(int, com[1:3])
		self.game = LifeGame(x, y)
		self.game_msg = await Client.send(msg, Client.get_field_msg(self.game))
		for e in Client.REACTIONS.items():
			await self.game_msg.add_reaction(e[1])

	@staticmethod
	def get_field_msg(game):
		cont = ''
		for x in range(game.x):
			for y in range(game.y):
				cont += Client.YELLOW_SQUARE if not game.running and game.cx == x and game.cy == y else Client.WHITE_SQUARE if game.field[x][y] else Client.BLACK_SQUARE
			if x != game.x - 1: cont += '\n'
		return cont

	async def update_game(self, com, msg):
		await self.update_field()

	async def start_game(self):
		self.game.running = not self.game.running
		while self.game.running:
			self.game.step()
			await self.update_field()

	@staticmethod
	async def send(msg, content):
		ch = msg.channel
		if isinstance(ch, discord.DMChannel):
			logger.debug(f'Received from User {msg.author} directly')
			ch = await msg.author.create_dm()
		return await ch.send(content)

	async def on_raw_reaction_add(self, r, *user):
		await self.on_reaction(self, r, user)

	async def on_raw_reaction_remove(self, r, *user):
		await self.on_reaction(self, r, user)

	async def on_reaction(self, client, r, something):
		if self.user.id != r.user_id and r.message_id == self.game_msg.id:
			self.process_reaction(r)

	async def process_reaction(self, r):
		if r.emoji.name == Client.REACTIONS['START']:
			await self.start_game()
		elif r.emoji.name == Client.REACTIONS['ARROW_LEFT']:
			self.game.cy = LifeGame.clamp(self.game.cy - 1, self.game.y)
		elif r.emoji.name == Client.REACTIONS['ARROW_RIGHT']:
			self.game.cy = LifeGame.clamp(self.game.cy + 1, self.game.y)
		elif r.emoji.name == Client.REACTIONS['ARROW_UP']:
			self.game.cx = LifeGame.clamp(self.game.cx - 1, self.game.x)
		elif r.emoji.name == Client.REACTIONS['ARROW_DOWN']:
			self.game.cx = LifeGame.clamp(self.game.cx + 1, self.game.x)
		elif r.emoji.name == Client.REACTIONS['REFRESH']:
			self.game.field = LifeGame.create_field(self.game.x, self.game.y)
		elif r.emoji.name == Client.REACTIONS['PICK']:
			i = self.game.field[self.game.cx][self.game.cy]
			self.game.field[self.game.cx][self.game.cy] = 0 if i else 1
		elif r.emoji.name == Client.REACTIONS['RANDOMIZE']:
			for y in range(self.game.y):
				for x in range(self.game.x):
					self.game.field[x][y] = random.randint(0, 1)
		await self.update_field()

	async def on_message(self, msg):
		logger.debug(f'Message received: [Content: {msg.content}]; [Arguments = {msg.content.split()}] {msg}')
		try:
			await self.process_message(msg)
		except Exception as e:
			error(e)
			await Client.send(msg, 'Invalid arguments received. Type #help-start for more details.')

	async def process_message(self, msg):
		c = msg.content
		if c[0] == '#':
			com = c[1:].split()
			if com[0] == 'start':
				await self.init_game(com, msg)
			elif com[0] == 'exit':
				logger.info('Logging out...')
				await Client.send(msg, 'Bot shutdowns...')
				await self.close()
			elif com[0] == 'help' or com[0] == 'info':
				await Client.send(msg, Client.HELP_TEMPLATE)
			elif com[0] == 'help-play':
				await Client.send(msg, Client.HELP_PLAY_TEMPLATE)
			else:
				raise Exception()


if __name__ == '__main__':
	try:
		Client().run(config.TOKEN)
	except Exception as e:
		error(e)
