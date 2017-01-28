# -*- coding: utf-8 -*-

from parsimonious.nodes import Node
from itertools import islice


def find(self, name, index=0, default=None):
    try:
        if index == 0:
            return next(self.findall(name))
        else:
            return next(islice(self.findall(name), index, index+1))
    except StopIteration:
        return default


def findall(self, name):
    if isinstance(name, str):
        return (c for c in self if c.expr_name == name)
    elif isinstance(name, set):
        return (c for c in self if c.expr_name in name)
    else:
        raise TypeError


def search(self, name, index=0, default=None):
    try:
        if index == 0:
            return next(self.searchall(name))
        else:
            return next(islice(self.searchall(name), index, index+1))
    except StopIteration:
        return default


def searchall(self, name):
    def func(node):
        if isinstance(name, str):
            if node.expr_name == name:
                yield node
        elif isinstance(name, set):
            if node.expr_name in name:
                yield node
        else:
            TypeError
        for child in node:
            yield from func(child)

    yield from func(self)


def prettily(self, error=None):
    def indent(text):
        return '\n'.join(('    ' + line) for line in text.splitlines())
    ret = [u'<%s%s matching "%s">%s' % (
        self.__class__.__name__,
        (' called "%s"' % self.expr_name) if self.expr_name else '',
        self.text.__repr__()[1:-1],
        '  <-- *** We were here. ***' if error is self else '')]
    for n in self:
        ret.append(indent(n.prettily(error=error)))
    return '\n'.join(ret)


def __getitem__(self, key):
    return self.children.__getitem__(key)


def __len__(self):
    return self.children.__len__()


def __bool__(self):
    return True


Node.find = find
Node.findall = findall
Node.search = search
Node.searchall = searchall
Node.prettily = prettily
Node.__getitem__ = __getitem__
Node.__len__ = __len__
Node.__bool__ = __bool__
