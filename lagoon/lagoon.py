# -*- coding: utf-8 -*-

import os
from parsimonious.grammar import Grammar
import logging

logging.basicConfig(
    filename='debug.log',
    filemode='w',
    level=logging.DEBUG)

# 文法の読み込み
path = os.path.dirname(__file__)
with open(os.path.join(path, 'grammar'), 'r', encoding='utf8') as f:
    grammar_code = f.read()
grammar = Grammar(grammar_code)
grammar_exp = Grammar('exp = _exp / _exp\n' + grammar_code)


def filter_node(node):
    """便宜のために再帰的にノードをふるいにかける"""
    new_children = []
    for index, child in enumerate(node):
        filter_node(child)
        # 子の名前が、無し・一文字以下・アンダーバー始まりのいずれかならば
        if not child.expr_name or len(child.expr_name) <= 1 or child.expr_name[0] == '_':
            # 子を削除し、孫を子として展開
            new_children.extend(child.children)
        else:
            new_children.append(child)
    node.children = new_children


def execute(file_path):
    """Lagoonファイルの実行"""
    from interpreter import LagoonFileInterpreter

    with open(file_path, 'r', encoding='utf8') as f:
        code = f.read()

    interpreter = LagoonFileInterpreter(file_path)
    return exec_(code, interpreter)


def exec_(code, interpreter):
    """Lagoonソースコードの実行"""
    logging.debug('...code...\n{}'.format(code))
    root_node = grammar.parse(code)
    # logging.debug('...raw_tree...\n{}'.format(root_node))
    filter_node(root_node)
    logging.debug('...tree...\n{}'.format(root_node))
    interpreter.run(root_node)
    # 名前空間の辞書を返す
    return interpreter.valid_namespace


def eval_(code, interpreter):
    """Lagoonソースコードの評価"""
    root_node = grammar_exp.parse(code)
    filter_node(root_node)
    # 評価結果を返す
    return interpreter.run(root_node)
