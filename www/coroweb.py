import os
import functools
import inspect
import logging
from urllib import parse
from aiohttp import web, asyncio

logging.basicConfig(level=logging.INFO)
# def get(path):
#     '''
#     define decorator @get('/path')
#     '''
#     def decorator(func):
#         @functools.wraps(func)
#         def wrapper(*args, **kw):
#             return func(*args, **kw)
#         wrapper.__method__ = 'GET'
#         wrapper.__route = path
#         return wrapper
#     return decorator

# post写法与get类似
# 或者使用偏函数：


def handler_decorator(path, *, method):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = method
        wrapper.__route__ = path
        return wrapper
    return decorator


get = functools.partial(handler_decorator, method='GET')
get = functools.partial(handler_decorator, method='POST')

# 使用inspect模块检查视图函数的参数
# inspect.Parameter.kind 类型
# POSITIONAL_ONLY        位置参数
# KEYWORD_ONLY           命名关键字参数
# VAR_POSITIONAL         可选参数 *args
# VAR_KEYWORD            关键字参数 **kw
# POSITIONAL_OR_KEYWORD  位置或必选参数


# 获取无默认值的命名关键词参数
def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


# 获取命名关键字参数
def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


# 判断是否有命名关键字参数
def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


# 判断是否有关键词参数
def has_var_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True


# 判断是否有名叫'request'的参数，且位置在最后
def has_request_args(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and(
            param.kind != inspect.Parameter.VAR_POSITIONAL and
            param.kind != inspect.Parameter.KEYWORD_ONLY and
            param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request param must be the last named param in function:%s%s' % (fn.__name__, str(sig)))
    return found


# 定义RequestHandler从视图中分析其需要接受的参数，从web.Request中获取必要的参数
# 调用视图函数，然后把结果转换为web.Response对象，符合aiohttp框架要求

class RequestHandler(object):
    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self. _required_kw_args = get_required_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._has_request_arg = has_request_args(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._has_var_kw_arg = has_var_kw_args(fn)

    # 定义kw用于保存参数
    # 判断视图函数是否存在关键词参数，如果存在根据POST或者GET方法将request请求内容保存到kw
    # 如果kw为空说明request无请求内容，则将match_info列表的资源映射给kw。若不为空，把命名关键词参数内容给kw
    async def __call__(self, request):
        # 定义kw用于保存request中的参数
        kw = None
        if self._has_named_kw_args or self._has_var_kw_arg:
            if request.method == 'POST':
                if request.content_type == None:
                    return web.HTTPBadRequest(text='missing content_type')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()  # 仅解析body字段的json数据
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params

                elif ct.startwith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
                if request.method == 'GET':
                    qs = request.query_string  # 返回URL查询语句?后的键值。string形式。
                    if qs:
                        kw = dict()
                        for k, v in parse.parse_qs(qs, True).items():  # True表示不忽略空格。
                            kw[k] = v[0]
                if kw is None:

                    # request.match_info返回dict对象。可变路由中的可变字段{variable}为参数名，传入request请求的path为值
                    # 若存在可变路由：/a/{name}/c，可匹配path为：/a/jack/c的request
                    # 则request.match_info返回{name = jack}
                    kw = dict(**request.match_info)
                else:
                    if self._has_named_kw_arg and (not self._has_var_kw_arg):
                        copy = dict()
                        # 只保留命名关键词参数
                        for name in self._named_kw_args:
                            if name in kw:
                                copy[name] = kw[name]
                        kw = copy
                    # 将request.match_info中的参数传入kw
                    for k, v in request.match_info.items():
                        # 检查kw中的参数是否和match_info中的重复
                        if k in kw:
                            logging.warn('Duplicate arg name in named arg and kw args: %s' % k)
                        kw[k] = v
                if self._has_request_arg:
                    kw['request'] = request
                if self._required_kw_args:
                    for name in self._required_kw_args:
                        if not name in kw:
                            return web.HTTPBadRequest('Missing argument: %s' % name)
                # 至此，kw为视图函数fn真正能调用的参数
                # request请求中的参数，终于传递给了视图函数
                logging.info('call with args: %s' % str(kw))
                from www.apis import APIError
                try:
                    r = await self._func(**kw)
                    return r
                except APIError as e:
                    return dict(error=e.error, data=e.data, message=e.message)


# 编写一个add_route函数，用来注册一个视图函数
def add_route(app, fn):
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if method is None or path is None:
        raise ValueError('@get or @post not defined in %s.' % fn.__name__)

    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        # 将fn转变成协程
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (
    method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
    # 在app中注册经RequestHandler类封装的视图函数
    app.router.add_route(method, path, RequestHandler(app, fn))


# 导入模块，批量注册视图函数
def add_routes(app, module_name):
    n = module_name.rfind('.')  # 从右侧检索，返回索引。若无，返回-1。
    # 导入整个模块
    if n == -1:
        # __import__ 作用同import语句，但__import__是一个函数，并且只接收字符串作为参数
        # __import__('os',globals(),locals(),['path','pip'], 0) ,等价于from os import path, pip
        mod = __import__(module_name, globals(), locals, [], 0)
    else:
        name = module_name[(n + 1):]
        # 只获取最终导入的模块，为后续调用dir()
        mod = getattr(__import__(module_name[:n], globals(), locals, [name], 0), name)
    # dir()迭代出mod模块中所有的类，实例及函数等对象,str形式
    for attr in dir(mod):
        if attr.startswith('_'):
            continue  # 忽略'_'开头的对象
        fn = getattr(mod, attr)
        # 确保是函数
        if callable(fn):
            # 确保视图函数存在method和path
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                # 注册
                add_route(app, fn)


# 添加静态文件，如image，css，javascript等
def add_static(app):
    # 拼接static文件目录
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))