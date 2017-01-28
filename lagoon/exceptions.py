# -*- coding: utf-8 -*-


class LagoonError(Exception):
    pass


class LagoonInterpreterError(LagoonError):
    pass


class LagoonNameError(LagoonError):
    pass


class LagoonTypeError(LagoonError):
    pass


class LagoonOtherError(LagoonError):
    pass
