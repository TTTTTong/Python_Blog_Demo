# -*- coding: utf-8 -*-
from www.orm import Model, StringField, IntegerField


class User(Model):
    __table__ = 'users'

    id = IntegerField(primary_Key=True)
    name = StringField()