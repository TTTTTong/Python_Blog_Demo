import hashlib
import logging
import re
import time
import json
from aiohttp import web

from www import markdown2
from www.apis import *
from www.config import configs
from www.coroweb import get, post
from www.models import User, Blog, next_id, Comment

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')
COOKIE_NAME = 'ansession'
_COOKIE_KEY = configs.session['secret']


def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError


def text2html(s):
    lines = map(lambda s: '<p>%s<p>' % s.replace('&', '%amp;').replace('<', '&lt;').replace('>', '&gt;'),\
                filter(lambda s: s.strip() != ''))
    return ''.join(lines)


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def user2cookie(user, max_age):
    expires = str(int(time.time()+max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode()).hexdigest()]
    return '-'.join(L)


async def cookie2user(cookie_str):
    '''
    'parse cookie and load user if cookie is valid
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        userid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(userid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (userid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode()).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None


@get('/')
def index(request):
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


@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    commnets = await Comment.findAll('blog_id=?', id, orderBy='created_at desc')
    for c in commnets:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'commetns': commnets
    }


@get('/manage/blogs/create')
def manage_create_blog():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blogs'
    }


@get('/api/blogs/{id}')
async def api_get_blog(*, id):
    blog = await Blog.find(id)
    return blog


@post('/api/create_blog')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip())
    await blog.save()
    return blog


@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }


@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }


@get('/signout')
def signout(request):
    referer = request.headers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    logging.info('user signed out')
    return r


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
    if not email:
        raise APIValueError('email', 'Invalid email')
    if not passwd:
        raise APIValueError('passwd', 'Invalid passwd')
    users = await User.findAll('email=?', email)
    if len(users) == 0:
        raise APIValueError('email', 'Invalid email')
    user = users[0]

    sha1 = hashlib.sha1()
    sha1.update(user.id.encode())
    sha1.update(b':')
    sha1.update(passwd.encode())
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid passwd')
    # set cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode()
    return r