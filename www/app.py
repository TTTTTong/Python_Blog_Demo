import datetime
import logging
import os
import time
import asyncio
import json
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from www import orm
from www.coroweb import add_routes, add_static

logging.basicConfig(level = logging.INFO)


def init_jinja2(app, **kw):
    logging.info('init jinja2.....')
    # class Environment(**options)
    options = dict(
        # 自动转义xml/html的特殊字符
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_String', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        # 自动加载修改后的模板文件
        auto_reload=kw.get('auto_reload', True)
    )

    # 获取模板文件路径
    path = kw.get('path', None)
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

    # Environment类是jinja2的核心类，用来保存配置、全局对象以及模板文件路径
    env = Environment(loader=FileSystemLoader(path), **options)
    # 过滤器集合
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f

    # 前面讲jinja2的环境配置都赋值给了env，都是为了给app添加__template__字段
    app['__template__'] = env


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta//60)
    if delta < 86400:
        return u'%s小时前' % (delta//3600)
    if delta < 604800:
        return u'%s天前' % (delta//86400)
    dt = datetime.datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)


# 用于输出日志的middleware, handler是视图函数
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return await handler(request)
    return logger


async def response_factory(app, handler):
    async def response(request):
        logging.info('response handler...')
        r = await handler(request)
        logging.info('response result = %s' % str(r))
        # StreamResponse是所有Response对象的父类
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            logging.info('*'*10)
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode())
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__', None)
            if template is None:
                # ensure_ascii：默认True，仅能输出ascii格式数据。故设置为False。
                # default：r对象会先被传入default中的函数进行处理，然后才被序列化为json对象
                # # __dict__：以dict形式返回对象属性和值的映射
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda obj:obj.__dict__).encode())
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                # 有模板信息，渲染模板
                resp = web.Response(body=app['__template__'].get_template(template).render(**r).encode())
                resp.content_type = 'text/html;charset=utf-8'
                return resp

        # 返回响应码
        if isinstance(r, int) and (100 <= r < 600):
            resp = web.Response(r)
            return resp
        # 反悔了响应码和原因，如(200, 'OK')
        if isinstance(r, tuple) and len(r) == 2:
            status_code, message = r
            if isinstance(status_code, int) and (100 <= status_code < 600):
                resp = web.Response(status_code, str(message))
                return resp
        # default:
        resp = web.Response(body=str(r).encode())
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

# async def auth_factory(app, handler):
#     async def auth(request):
#         logging.info('check user: %s %s' % (request.method, request.path))
#         request.__user__ = None
#         cookie_str = request.cookies.get(COOKIE_NAME, None)


async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request from: %s' % str(request.__data__))
        return await handler(request)
    return parse_data


async def init(loop):
    await orm.create_pool(loop=loop)
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()