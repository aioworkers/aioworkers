import random
import time
from os import getenv

from aiographite.aiographite import connect
from aiographite.protocol import PlaintextProtocol

GRAPHITE_HOST = getenv('GRAPHITE_HOST', 'localhost')


async def run(worker, *args, **kwargs):
    value = random.randrange(10)
    try:
    	connection = await connect(GRAPHITE_HOST, 2003, PlaintextProtocol(), loop=worker.loop)
    	await connection.send('workers.worker', value, time.time())
    	await connection.close()
    except Exception as e:
    	worker.logger.error('Cannot connect to graphite')
