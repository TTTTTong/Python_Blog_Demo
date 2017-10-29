import hashlib
import re
import time
import json
from aiohttp import web
from www.apis import *
from www.config import configs
from www.coroweb import get, post
from www.models import User, Blog, next_id

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
COOKIE_NAME = 'ansession'
_COOKIE_KEY = configs.session['secret']


def user2cookie(user, max_age):
    expires = str(int(time.time()+max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode()).hexdigest()]
    return '-'.join(L)


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


@get('/register')
async def register():
    return {
        '__template__': 'register.html'
    }


@post('/api/register_user')
async def register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', email)
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'email is already in use')
    uuid = next_id()
    sha1_passwd = '%s:%s' % (uuid, passwd)
    user = User(id=uuid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode()).hexdigest(), image='about:blank')
    await user.save()
    # make session cookie:
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '*********'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode()
    return r


@post('/api/authenticate')
async def authenticate(*, email, passwd):
