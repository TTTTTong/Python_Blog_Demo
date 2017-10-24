import functools
import inspect
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


