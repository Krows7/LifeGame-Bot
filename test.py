from unittest.mock import Mock, MagicMock
from unittest import TestSuite, TextTestRunner, IsolatedAsyncioTestCase
from copy import deepcopy
from bot import LifeGame, Client


async def async_magic():
    pass

MagicMock.__await__ = lambda x: async_magic().__await__()


def create_message_mock():
    msg = MagicMock()
    msg.channel = MagicMock()
    return msg


def create_reaction_mock():
    r = MagicMock()
    r.user_id = 0
    r.message_id = 0
    r.emoji = MagicMock()
    return r


async def send_mock(x, y):
    return x


async def assert_reaction(client, r, name, call):
    r.emoji.name = Client.REACTIONS[name]
    await client.process_reaction(r)
    assert call()


async def assert_message(case, ex, client, msg, content, call=None):
    msg.content = content
    with case.assertRaises(ex) as e:
        await client.process_message(msg)
    if call: assert call()


class Test(IsolatedAsyncioTestCase):

    def setUp(self):

        self.game = LifeGame(5, 5)
        self.game.field = [[0, 0, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 1, 0], [0, 1, 1, 1, 0], [0, 0, 0, 0, 0]]
        self.client = Client()
        self.client.game = self.game
        self.client._game_msg = MagicMock()
        self.client._game_msg.id = 0
        self.client._game_msg.add_reaction = Mock()
        self.client._user = MagicMock()
        self.client._user.id = 0

        self.test_msg = create_message_mock()
        self.test_reaction = create_reaction_mock()

        Client.send = send_mock

    def test_life(self):

        assert LifeGame.create_field(1, 0) == [[]]
        assert LifeGame.create_field(2, 2) == [[0, 0], [0, 0]]
        assert LifeGame.clamp(5, 6) == 5
        assert LifeGame.clamp(6, 6) == 0
        assert LifeGame.clamp(- 1, 6) == 5

        assert self.game.neighbour_count(0, 0) == 0
        assert self.game.neighbour_count(2, 2) == 5
        assert self.game.neighbour_count(2, 1) == 3
        assert self.game.neighbour_count(3, 3) == 2

    async def test_client(self):

        self.game.step()
        assert self.game.field == [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 1, 0, 1, 0], [0, 0, 1, 1, 0], [0, 0, 1, 0, 0]]
        assert Client.get_field_msg(self.client.game) == Client.YELLOW_SQUARE + Client.BLACK_SQUARE * 4 + '\n' + Client.BLACK_SQUARE * 5 + '\n' + Client.BLACK_SQUARE + Client.WHITE_SQUARE + Client.BLACK_SQUARE + Client.WHITE_SQUARE + Client.BLACK_SQUARE + '\n' + Client.BLACK_SQUARE * 2 + Client.WHITE_SQUARE * 2 + Client.BLACK_SQUARE + '\n' + Client.BLACK_SQUARE * 2 + Client.WHITE_SQUARE + Client.BLACK_SQUARE * 2

        await assert_message(self, Exception, self.client, self.test_msg, '#something')
        await assert_message(self, Exception, self.client, self.test_msg, '#start')
        await assert_message(self, Exception, self.client, self.test_msg, '#start not numbers')
        await assert_message(self, Exception, self.client, self.test_msg, '#')

        await self.client.init_game([None, '1', '3'], self.test_msg)
        assert self.client.game.field == [[0, 0, 0]]
        assert self.client.game_msg.add_reaction.call_count == 8

        old_field = deepcopy(self.client.game.field)

        await assert_reaction(self.client, self.test_reaction, 'PICK', lambda: self.client.game.field[0][0] == 1)
        await assert_reaction(self.client, self.test_reaction, 'ARROW_LEFT', lambda: self.client.game.cy == 2)
        await assert_reaction(self.client, self.test_reaction, 'ARROW_RIGHT', lambda: self.client.game.cy == 0)
        await assert_reaction(self.client, self.test_reaction, 'ARROW_UP', lambda: self.client.game.cx == 0)
        await assert_reaction(self.client, self.test_reaction, 'ARROW_DOWN', lambda: self.client.game.cx == 0)
        await assert_reaction(self.client, self.test_reaction, 'RANDOMIZE', lambda: self.client.game.field != old_field)
        await assert_reaction(self.client, self.test_reaction, 'REFRESH', lambda: self.client.game.field == LifeGame.create_field(self.client.game.x, self.client.game.y))


def suite():

    suite = TestSuite()
    suite.addTest(Test('test_life'))
    suite.addTest(Test('test_client'))

    return suite


if __name__ == '__main__':

    TextTestRunner().run(suite())
