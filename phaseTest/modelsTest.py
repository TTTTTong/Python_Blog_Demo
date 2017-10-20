import asyncio

from www.models import *
from www import orm


async def test(loop):
    await orm.create_pool(loop, user='root', password='201919', database='pythonblog')

    u = User(name='Test', email='xiaoyu@gmail.com', passwd='tong201919', image='about:blank')
    await u.save()
    await orm.destory_pool()


loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()