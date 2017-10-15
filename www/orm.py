import asyncio, logging
import aiomysql


def log(sql, args=()):
    logging.info('SQL: %s' % sql)


@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            result = yield from cur.fetchmany(size)
        else:
            result = yield from cur.fetcgall()
        yield from cur.close()
        repr()
        logging.info('rows returned: %s' % len(result))
        return result


@asyncio.coroutine
def execute(sql, args):
    log(sql)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount()
            yield from cur.close()
        except BaseException as e:
            raise
        return affected


class ModelMetaClass(type):
    def __new__(cls, name, bases, attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 取出表名 默认与类名相同
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 用于存储所有的字段以及字段值
        mapping = dict()
        # 仅用来存储非主键以外的其他字段，而且只存key
        fields = []
        # 仅保存主键的key
        primaryKey = None
        for k,v in attrs.items():
            if isinstance(v, Field):
                mapping[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Douplicate primary key for field:%s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        # 保证必须有一个主键
        if not primaryKey:
            raise RuntimeError('not found primary key')
        # 防止实例变量与类属性冲突，所以将其去掉
        for k in mapping.keys():
            attrs.pop(k)
        # 以下都是要返回的东西了，刚刚记录下的东西，如果不返回给这个类，又谈得上什么动态创建呢？
        # 到此，动态创建便比较清晰了，各个子类根据自己的字段名不同，动态创建了自己
        # 下面通过attrs返回的东西，在子类里都能通过实例拿到，如self
        escaped_fields = list(map(lambda f : '%s' % f, fields))
        attrs['__mappings__'] = mapping
        attrs['__table__'] = tableName
        attrs['__primaryKey__'] = primaryKey
        attrs['__fields__'] = fields
        # 只是为了编写Model方便，放在元类里和放在Model里都可以
        # attrs['__select__'] = "select %s ,%s from %s " % (
        # primaryKey, ','.join(map(lambda f: '%s' % (mapping.get(f).name or f), fields)), tableName)
        # attrs['__update__'] = "update %s set %s where %s=?" % (
        # tableName, ', '.join(map(lambda f: '`%s`=?' % (mapping.get(f).name or f), fields)), primaryKey)
        # attrs['__insert__'] = "insert into %s (%s,%s) values (%s);" % (
        # tableName, primaryKey, ','.join(map(lambda f: '%s' % (mapping.get(f).name or f), fields)),
        # create_args_string(len(fields) + 1))
        # attrs['__delete__'] = "delete from %s where %s= ? ;" % (tableName, primaryKey)
        attrs['__select__'] = 'select %s, %s from %s' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (\
        tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update %s set %s where %s=?' % (\
        tableName, ', '.join(map(lambda f: '%s = ?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from %s where %s =?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)