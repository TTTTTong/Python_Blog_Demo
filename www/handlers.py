import time

from www.coroweb import get
from www.models import User, Blog


@get('/')
async def index(request):
    summary = 'Lorem ipsum dolor sit amet, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summar=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summar=summary, created_at=time.time()-7200),
    ]
    return {
        '__template__': 'blog.html',
        'blogs': blogs
    }