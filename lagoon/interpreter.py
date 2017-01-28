# -*- coding: utf-8 -*-

import monkeypatch  # noqa
import exceptions

import importlib
import collections
import functools
import argparse
import re


RefChainElem = collections.namedtuple('RefChainElem', 'name')
NodeChainElem = collections.namedtuple('NodeChainElem', 'node')
CallChainElem = collections.namedtuple('CallChainElem', 'arg_nodes')
AttrChainElem = collections.namedtuple('AttrChainElem', 'name')
IndexChainElem = collections.namedtuple('IndexChainElem', 'key')

NameAssign = collections.namedtuple('NameAssign', 'name')
AttrAssign = collections.namedtuple('AttrAssign', 'obj, name')
IndexAssign = collections.namedtuple('IndexAssign', 'obj, index')


# 代入時のカンマ区切り
class AssignTuple(tuple):
    pass


class Continued(object):

    def __init__(self):
        pass

    @property
    def valid(self):
        return True


class Broken(Continued):

    def __init__(self, depth):
        super().__init__()
        self.depth = depth

    @property
    def valid(self):
        return self.depth > 0


class Returned(Broken):

    def __init__(self, result):
        super().__init__(float('INF'))
        self.result = result


class LagoonTable(argparse.Namespace):

    """
    Lagoonのtable構造
    attributeでアクセスできる
    AttributeErrorのとき要素metatableがあればそちらを読みに行く
    他のLagoonTableに追加されたとき、それを親として記憶する
    （すでに親が存在する場合は上書きする）
    """

    def __getattr__(self, name):
        try:
            getter = object.__getattribute__(self, 'get_{}'.format(name))
            return getter(current=self)
        except AttributeError:
            try:
                metatable = object.__getattribute__(self, 'metatable')
                return getattr(metatable, name)
            except AttributeError:
                raise

    def __setattr__(self, name, value):
        if isinstance(value, LagoonTable):
            if name != 'parent':
                setattr(value, 'parent', self)
        try:
            setter = getattr(self, 'set_{}'.format(name))
            object.__setattr__(self, name, setter(value, current=self))
        except AttributeError:
            object.__setattr__(self, name, value)

    def __delattr__(self, name):
        value = getattr(self, name)
        if isinstance(value, LagoonTable):
            if name != 'parent':
                delattr(value, 'parent')
        object.__delattr__(self, name)


class LagoonCallable(object):
    pass


class LagoonFunction(LagoonCallable):

    """
    Lagoonの関数
    名前空間を保持する（レキシカルスコープ）
    """

    def __init__(self, block_node, arg_names,
                 static_defaults, dynamic_defaults, interpreter):
        self.block_node = block_node
        self.arg_names = arg_names
        self.static_defaults = static_defaults
        self.dynamic_defaults = dynamic_defaults
        self.interpreter = interpreter

    def __call__(self, *args, **kwargs):
        arg_namespace = {}
        arg_namespace.update(self.static_defaults)
        arg_namespace.update({k: self.interpreter.run(v)
                              for k, v in self.dynamic_defaults.items()})
        arg_namespace.update(zip(self.arg_names, args))
        arg_namespace.update(kwargs)
        arg_namespace['args'] = args
        arg_namespace['current'] = kwargs.get('current', None)
        namespaces = self.interpreter.namespaces + [arg_namespace]
        result = LagoonInterpreter(namespaces).run(self.block_node)
        if isinstance(result, Returned):
            return result.result
        else:
            return result


class AbstractInterpreter(object):

    """
    機能未実装のインタプリタ
    """

    def run(self, node):
        """ノードの実行"""
        # nodeに対する自クラスのvisitメソッドを呼び出す
        visit = getattr(self, 'visit_{}'.format(node.expr_name))
        return visit(node)


class LagoonInterpreter(AbstractInterpreter):

    """
    Lagoonのインタプリタ
    """

    def __init__(self, namespaces):
        self.namespaces = namespaces
        self.valid_namespace = collections.ChainMap(*reversed(self.namespaces))

    def run(self, node):
        self.last_node = node
        return super().run(node)

    def importall(self, module_name):
        module = importlib.import_module(module_name)
        for method_name in dir(module):
            self.assign(NameAssign(method_name), value=getattr(module, method_name))

    def loadall(self, filepath):
        module = self.load_(filepath)
        for method_name in dir(module):
            self.assign(NameAssign(method_name), value=getattr(module, method_name))

    def load_(self, filepath):
        import lagoon
        from os.path import join, normpath, dirname
        namespace = lagoon.execute(
            normpath(join(dirname(self.valid_namespace['__lagoonfile__']), filepath)))
        return argparse.Namespace(**namespace)

    def exec_(self, code):
        import lagoon
        return lagoon.exec_(code, self)

    def eval_(self, code):
        import lagoon
        return lagoon.eval_(code, self)

    # general:

    def visit_program(self, node):
        try:
            block_node = node.find('block')
            if block_node:
                self.run(block_node)
        except exceptions.LagoonInterpreterError:
            raise
        except:
            code = self.last_node.full_text[:self.last_node.start]
            lineno = code.count('\n') + 1
            colno = len(re.match(r'[^\n]*', code[::-1]).group(0))
            raise exceptions.LagoonInterpreterError(
                'error at line {0}, column {1}'.format(lineno, colno))

    def visit_block(self, node):
        for child_node in node:
            result = self.run(child_node)
            if isinstance(result, Continued) and result.valid:
                return result
        return result

    def visit_comm(self, node):
        pass

    def visit_stat(self, node):
        return self.run(node[0])

    def visit_exp(self, node):
        return self.run(node[0])

    # operator:

    def visit_range(self, node, is_slice=False):
        start_node = node.find('range_start')
        stop_node = node.find('range_stop')
        start = self.run(start_node[0]) if start_node else 0
        stop = self.run(stop_node[0])
        range_ope_node = node.find('range_ope')
        range_ope_name = range_ope_node[0].expr_name
        func = slice if is_slice else range
        if range_ope_name == 'range_ope_opened':
            return func(start, stop)
        elif range_ope_name == 'range_ope_closed':
            return func(start, stop + 1)
        else:
            assert False

    def chain(self, chain_elems):
        chain_elems = iter(chain_elems)
        chain_elem = next(chain_elems)
        if isinstance(chain_elem, RefChainElem):
            result = self.reference(chain_elem.name)
        elif isinstance(chain_elem, NodeChainElem):
            result = self.run(chain_elem.node)
        else:
            assert False

        for chain_elem in chain_elems:
            if isinstance(chain_elem, CallChainElem):
                args = []
                kwargs = {}
                for arg_node in chain_elem.arg_nodes:
                    key_node = arg_node.find('name')
                    value_node = arg_node.find('exp')
                    if key_node:
                        kwargs[self.run(key_node)] = self.run(value_node)
                    else:
                        args.append(self.run(value_node))
                result = result(*args, **kwargs)
            elif isinstance(chain_elem, AttrChainElem):
                new_result = getattr(result, chain_elem.name)
                if isinstance(new_result, LagoonCallable):
                    new_result = functools.partial(new_result, current=result)
                result = new_result
            elif isinstance(chain_elem, IndexChainElem):
                result = result[chain_elem.key]
            else:
                assert False
        return result

    def chain_elems(self, node):
        chain_elems = []
        for child in node.children:
            if child.expr_name == 'call_paren':
                chain_elems.append(CallChainElem(child.findall('call_paren_arg')))
            elif child.expr_name == 'attr_dot':
                chain_elems.append(AttrChainElem(self.run(child[0])))
            elif child.expr_name == 'index_ope':
                chain_elems.append(IndexChainElem(self.run(child[0])))
            else:
                if child.expr_name in {'symbolattr_name', 'symbolindex_name'}:
                    chain_elems.extend(self.run(child))
                elif child.expr_name == 'ref_name':
                    chain_elems.append(RefChainElem(child.text))
                else:
                    chain_elems.append(NodeChainElem(child))
        return chain_elems

    def visit_chain(self, node):
        return self.chain(self.chain_elems(node))

    def common_symbol_name(self, node, access_type):
        assert access_type in {'attr', 'index'}
        chain_elems = []
        children = iter(node.children)
        child = next(children)
        chain_elems.append(RefChainElem(self.run(child)))
        for child in children:
            if access_type == 'attr':
                chain_elems.append(AttrChainElem(self.run(child)))
            elif access_type == 'index':
                chain_elems.append(IndexChainElem(self.run(child)))
        return chain_elems

    def visit_symbolattr_name(self, node):
        return self.common_symbol_name(node, 'attr')

    def visit_symbolindex_name(self, node):
        return self.common_symbol_name(node, 'index')

    def visit_symbolattr(self, node):
        symbols = {'$': 'globalvars', '@': 'current', '^': 'parent'}
        return symbols[node.text]

    def visit_symbolindex(self, node):
        symbols = {'%': 'args'}
        return symbols[node.text]

    def visit_pow(self, node):
        return self.run(node[0]) ** self.run(node[1])

    def visit_pos(self, node):
        return +self.run(node[0])

    def visit_neg(self, node):
        return -self.run(node[0])

    def visit_mul(self, node):
        return self.run(node[0]) * self.run(node[1])

    def visit_truediv(self, node):
        return self.run(node[0]) / self.run(node[1])

    def visit_mod(self, node):
        return self.run(node[0]) % self.run(node[1])

    def visit_add(self, node):
        return self.run(node[0]) + self.run(node[1])

    def visit_sub(self, node):
        return self.run(node[0]) - self.run(node[1])

    def visit_lt(self, node):
        return self.run(node[0]) < self.run(node[1])

    def visit_le(self, node):
        return self.run(node[0]) <= self.run(node[1])

    def visit_eq(self, node):
        return self.run(node[0]) == self.run(node[1])

    def visit_ne(self, node):
        return self.run(node[0]) != self.run(node[1])

    def visit_ge(self, node):
        return self.run(node[0]) >= self.run(node[1])

    def visit_gt(self, node):
        return self.run(node[0]) > self.run(node[1])

    def visit_is_(self, node):
        return self.run(node[0]) is self.run(node[1])

    def visit_contains(self, node):
        return self.run(node[0]) in self.run(node[1])

    def visit_not_(self, node):
        return not self.run(node[0])

    def visit_and_(self, node):
        return self.run(node[0]) and self.run(node[1])

    def visit_or_(self, node):
        return self.run(node[0]) or self.run(node[1])

    def visit_isa(self, node):
        return isinstance(self.run(node[0]), self.run(node[1]))

    def visit_one_if(self, node):
        return self.run(node[0]) if self.run(node[1]) else self.run(node[2])

    def visit_one_try(self, node):
        try:
            return self.run(node[0])
        except self.run(node[1]):
            return self.run(node[2])

    # statement:

    def assign(self, assignment, value):
        if isinstance(assignment, NameAssign):
            self.valid_namespace[assignment.name] = value
        elif isinstance(assignment, AttrAssign):
            setattr(assignment.obj, assignment.name, value)
        elif isinstance(assignment, IndexAssign):
            assignment.obj[assignment.key] = value
        elif isinstance(assignment, (list, tuple)):
            try:
                is_valid = len(assignment) == len(value)
            except TypeError:
                raise exceptions.LagoonTypeError(
                    'Cannot multiple assign: value must be sequence')
            if is_valid:
                for assignment_, value_ in zip(assignment, value):
                    self.assign(assignment_, value_)
            else:
                raise exceptions.LagoonTypeError(
                    'Cannot multiple assign: length missmatch')
        else:
            assert False

    def visit_assign(self, node):
        left_node = node.find('assign_left')
        right_node = node.find('assign_right')
        left = self.run(left_node)
        right = self.run(right_node)
        ope_name = node.find('assign_ope')[0].expr_name
        if ope_name != 'assign_ope_':
            if isinstance(left, list):
                raise exceptions.LagoonOtherError(
                    'combined assign operator cannot used for multiple assignment')
            else:
                left_value = self.run(left_node[0])
                if ope_name == 'assign_ope_add':
                    right += left_value
                elif ope_name == 'assign_ope_sub':
                    right -= left_value
                elif ope_name == 'assign_ope_mul':
                    right *= left_value
                elif ope_name == 'assign_ope_div':
                    right /= left_value
        return self.assign(assignment=left, value=right)

    def visit_assign_left(self, node):
        chain_nodes = node.findall('chain')
        assigns = []
        for chain_node in chain_nodes:
            chain_elems = self.chain_elems(chain_node)
            init = chain_elems[0:-1]
            tail = chain_elems[-1]
            if init:
                if isinstance(tail, AttrChainElem):
                    assigns.append(AttrAssign(self.chain(init), tail.name))
                elif isinstance(tail, IndexChainElem):
                    assigns.append(IndexAssign(self.chain(init), tail.key))
                else:
                    assert False
            else:
                if isinstance(tail, RefChainElem):
                    assigns.append(NameAssign(tail.name))
                else:
                    assert False
        return assigns[0] if len(assigns) < 2 else assigns

    def visit_assign_right(self, node):
        value_nodes = node.findall('exp')
        values = AssignTuple(self.run(n) for n in value_nodes)
        return values[0] if len(values) < 2 else values

    def visit_if(self, node):
        pairs = [(n.find('exp'), n.find('block'))
                 for n in node.findall({'if_if', 'if_elseif', 'if_else'})]
        for condition_node, block_node in pairs:
            if condition_node is None or self.run(condition_node):
                return self.run(block_node)

    def visit_while(self, node):
        condition_node = node.find('exp')
        block_node = node.find('block')
        while self.run(condition_node):
            result = self.run(block_node)
            if isinstance(result, Broken) and result.valid:
                result.depth -= 1
                return result

    def visit_for(self, node):
        assign_node = node.find('assign_left')
        container_node = node.find('exp')
        block_node = node.find('block')
        for value in self.run(container_node):
            self.assign(self.run(assign_node), value=value)
            result = self.run(block_node)
            if isinstance(result, Broken) and result.valid:
                result.depth -= 1
                return result

    def visit_times(self, node):
        times_node = node.find('exp')
        block_node = node.find('block')
        times = self.run(times_node)
        if not isinstance(times, int):
            raise exceptions.LagoonTypeError('Number of times to repeat must be int')
        for _ in range(times):
            result = self.run(block_node)
            if isinstance(result, Broken) and result.valid:
                result.depth -= 1
                return result

    def visit_continue(self, node):
        return Continued()

    def visit_break(self, node):
        depth_node = node.find('exp')
        if depth_node:
            depth = self.run(depth_node)
            if not isinstance(depth, int):
                raise exceptions.LagoonTypeError('Depth must be int')
            return Broken(depth)
        else:
            return Broken(1)

    def visit_return(self, node):
        result_node = node.find('exp')
        if result_node:
            result = self.run(result_node)
            return Returned(result)
        else:
            return Returned(None)

    def visit_try(self, node):
        try_node = node.find('try_try')
        except_nodes = node.findall('try_except')
        try:
            block_node = try_node.find('block')
            assert block_node
            return self.run(block_node)
        except Exception as e:
            for except_node in except_nodes:
                exception_node = except_node.find('exp')
                exception = self.run(exception_node) if exception_node else None
                name_node = except_node.find('name')
                name = self.run(name_node) if name_node else None
                block_node = except_node.find('block')
                assert block_node
                if not exception or (exception and isinstance(e, exception)):
                    if name:
                        self.assign(NameAssign(name), value=e)
                    return self.run(block_node)
                    break
            else:
                raise e

    def visit_raise(self, node):
        result_node = node.find('exp')
        if result_node:
            result = self.run(result_node)
            raise result
        else:
            raise

    def visit_assert(self, node):
        result_node = node.find('exp')
        if result_node:
            result = self.run(result_node)
            if not result:
                raise AssertionError
        else:
            raise AssertionError

    # expression:

    def visit_number(self, node):
        if '.' in node.text:
            return float(node.text)
        else:
            return int(node.text)

    # Re for visit_string
    interpolation_pattern = r'#\{([^\}]*)\}'
    interpolation_re = re.compile(interpolation_pattern)

    def visit_string(self, node):
        # 式展開

        def interpolation(string):
            return self.interpolation_re.sub(lambda m: str(self.eval_(m.group(1))), string)

        string = self.run(node.find('string_body')[0])
        macros = self.run(node.find('string_macros'))
        if 'i' in macros:
            string = interpolation(string)
        if 'a' in macros or 'd' in macros:
            from textwrap import dedent
            string = dedent(string)
        if 'a' in macros or 'l' in macros:
            string = string.lstrip('\n')
        if 'a' in macros or 'r' in macros:
            string = string.rstrip('\n')
        if '~' in macros:
            string = re.compile(string)
        if 'b' in macros:
            string = string.encode('utf8')
        return string

    def visit_string_macros(self, node):
        return node.text

    def visit_sq_heredoc(self, node):
        return node.find('sq_heredoc_contents').text

    def visit_dq_heredoc(self, node):
        return (node.find('dq_heredoc_contents').text
                .encode('raw_unicode_escape').decode('unicode_escape'))

    def visit_sq_string(self, node):
        return node.find('sq_string_contents').text

    def visit_dq_string(self, node):
        return (node.find('dq_string_contents').text
                .encode('raw_unicode_escape').decode('unicode_escape'))

    def visit_heredoc(self, node):
        return node.find('heredoc_contents').text

    def visit_sequence(self, node):
        return self.run(node[0]) if len(node) else iter(())

    def common_visit_gen(self, node, struct_type):
        assert struct_type in {'sequence', 'mapping'}
        for_node = node.find('{}_gen_for'.format(struct_type))
        if struct_type == 'sequence':
            elem_node = for_node.find('exp') if for_node else None
        elif struct_type == 'mapping':
            key_node = for_node.find('exp', 0) if for_node else None
            value_node = for_node.find('exp', 1) if for_node else None
        in_node = node.find('{}_gen_in'.format(struct_type))
        assign_node = in_node.find('assign_left')
        assign = self.run(assign_node)
        container_node = in_node.find('exp')
        container = self.run(container_node)

        if_node = node.find('{}_gen_if'.format(struct_type))
        condition_node = if_node.find('exp') if if_node else None

        def gen():
            for item in container:
                self.assign(assign, value=item)
                if not condition_node or self.run(condition_node):
                    if for_node:
                        if struct_type == 'sequence':
                            yield self.run(elem_node)
                        elif struct_type == 'mapping':
                            yield (self.run(key_node), self.run(value_node))
                    else:
                        yield item

        return gen()

    def visit_sequence_gen(self, node):
        return self.common_visit_gen(node, 'sequence')

    def visit_sequence_items(self, node):
        return (self.run(c) for c in node.findall('exp'))

    def visit_list(self, node):
        return list(self.run(node[0]))

    def visit_tuple(self, node):
        return tuple(self.run(node[0]))

    def visit_set(self, node):
        return set(self.run(node[0]))

    def visit_frozenset(self, node):
        return frozenset(self.run(node[0]))

    def visit_generator(self, node):
        return self.run(node[0])

    def visit_mapping(self, node):
        return self.run(node[0]) if len(node) else iter(())

    def visit_mapping_gen(self, node):
        return self.common_visit_gen(node, 'mapping')

    def visit_mapping_items(self, node):
        mapping_item_nodes = node.findall('mapping_item')
        return ((self.run(n.find('exp', 0)), self.run(n.find('exp', 1)))
                for n in mapping_item_nodes)

    def visit_table(self, node):
        table_item_nodes = node.findall('table_item')
        pairs = {self.run(n.find('name')): self.run(n.find('exp'))
                 for n in table_item_nodes}
        return LagoonTable(**pairs)

    def visit_dict(self, node):
        return dict(self.run(node[0]))

    def visit_ordereddict(self, node):
        return collections.OrderedDict(self.run(node[0]))

    def visit_callable(self, node):
        callable_arg_nodes = node.findall('callable_arg')
        arg_tuples = [tuple(n.find(e) for e in ('name', 'callable_arg_ope', 'exp'))
                      for n in callable_arg_nodes]
        arg_names = []
        static_defaults = {}
        dynamic_defaults = {}
        for name_node, arg_ope_node, value_node in arg_tuples:
            arg_name = self.run(name_node)
            arg_names.append(arg_name)
            if arg_ope_node:
                arg_ope_name = arg_ope_node[0].expr_name
                if arg_ope_name == 'callable_arg_ope_static':
                    static_defaults[arg_name] = self.run(value_node)
                elif arg_ope_name == "callable_arg_ope_dynamic":
                    dynamic_defaults[arg_name] = value_node
                else:
                    assert False
        block_node = node.find('block')
        # Callableの種類が増えた場合はここで振り分ける
        Callable = LagoonFunction
        return Callable(block_node, arg_names,
                        static_defaults, dynamic_defaults, self)

    def visit_numbered_arg(self, node):
        try:
            return self.valid_namespace['args'][self.run(node.find('number'))]
        except KeyError:
            raise exceptions.LagoonOtherError(
                'Numbered argument symbol must be within block')
        except IndexError:
            raise exceptions.LagoonTypeError(
                'Numbered argument not satisfied')

    # characters

    def reference(self, name):
        try:
            return self.valid_namespace[name]
        except KeyError:
            raise exceptions.LagoonNameError(
                '{} is currently not defined'.format(name))

    def visit_ref_name(self, node):
        return self.reference(node.text)

    def visit_name(self, node):
        return node.text


class LagoonFileInterpreter(LagoonInterpreter):

    def __init__(self, file_path):
        # 準備
        import builtins
        import operator

        self.lineno = 0
        self.colno = 0

        # Lagoonのビルトインを定義
        self.builtin_namespace = {
            'py': builtins,
            'op': operator,

            'import': importlib.import_module,
            'importall': self.importall,
            'load': self.load_,
            'loadall': self.loadall,
            'exec': self.exec_,
            'eval': self.eval_,

            'all': all,
            'any': any,
            'bool': bool,
            'complex': complex,
            'delattr': delattr,
            'Dict': dict,
            'divmod': divmod,
            'enumerate': enumerate,
            'pyeval': eval,
            'pyexec': exec,
            'filter': filter,
            'Float': float,
            'FrozenSet': frozenset,
            'getattr': getattr,
            'hasattr': hasattr,
            'hash': hash,
            'Int': int,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'iter': iter,
            'len': len,
            'List': list,
            'map': map,
            'max': max,
            'min': min,
            'next': next,
            'open': open,
            'print': print,
            'range': range,
            'reversed': reversed,
            'round': round,
            'Set': set,
            'setattr': setattr,
            'slice': slice,
            'sorted': sorted,
            'Str': str,
            'sum': sum,
            'Tuple': tuple,
            'type': type,
            'zip': zip,

            'true': True,
            'false': False,
            'none': None,
            'inf': float('INF'),

            '__lagoonfile__': file_path,
            '__interpreter__': self,

            'globalvars': argparse.Namespace(),
        }

        super().__init__(namespaces=[self.builtin_namespace, {}])
