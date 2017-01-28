![logo](logo.jpg)

[image source](https://pixabay.com/en/air-bubbles-diving-underwater-blow-230014/)

# Lagoon

LagoonはPython上で動作するプログラミング言語です。

## 0. 動作環境

Python 3.4以上
PIPで `parsimonious` をインストールしてください。

## 1. 基本

### 実行

```
python lagoon file.lgn
```

### 表示

```
print("foo")
```

### 代入

代入演算子として`=`, `+=`, `-=`, `*=`, `/=`が使用できます。  
多重代入が可能です。多重代入のとき`+=`, `-=`, `*=`, `/=`は使用できません。

```
foo = 100
foo += 100
foo, bar = 100, 200
```

### コメント

複数行コメントでは、スペースを入れることで容易にコメントを解除することができます。

```
# comment
#!--
multiline
    comment.
#--
# !--
print("Easy way to uncomment.")
#--
```

## 2. リテラル

### 数値

小数点以下があれば`Int`、なければ`Float`になります。少数点以前は省略できません。

```
a = 1
b = 1.0
```

### 文字列

`'foo'`はほとんどエスケープを行いません。`"foo"`はエスケープを行います。  
複数行の文字列は３連クォーテーション`'''foo'''`, `"""foo"""`です。  
リテラルの直前に、各一文字のマクロを一つまたは複数指定することができます。  

マクロ（実行順） | 意味 | 機能
--- | ---
i | interpolation | 文字列中の`#{}`に対して式展開を行います。
d | dedent | 自動ディデントを行います。
l | lstrip | 文字列の最初の連続する改行を取り除きます。
r | rstrip | 文字列の最後の連続する改行を取り除きます。
a | auto | マクロd, l, rをこの順に全て実行します。
~ | - | 正規表現オブジェクトへコンパイルします。
b | bytes | UTF-8でエンコードしてバイト列にします。

```
s0 = 'foo\nbar'
s1 = "foo\nbar"
s2 = i"1 + 1 = #{1 + 2}"
s3 = a"""
    multiline
        string.
"""
r = ~'s.*e'.match('snake')
```

### シーケンス

`[foo, bar]`のようにシーケンスを表現できます。  
シーケンスはデフォルトでリストになりますが、リテラルの直前に一文字の識別子を
付加することで、他の構造を表現することもできます。  
区切り文字として、コンマまたは改行を使用できます。

識別子 | 意味 | 構造
--- | --- | ---
l | list | リスト
t | tuple | タプル
s | set | 集合
f | frozen set | 変更不可能な集合
g | generator | ジェネレータ

```
l = [1, 2, 3]
t = t[4, 5, 6]
s = s[]
```

### マッピング

`[foo: 0, bar: 1]`のようにマッピングを表現できます。  
マッピングはデフォルトで辞書になりますが、リテラルの直前に一文字の識別子を
付加することで、他の構造を表現することもできます。  
区切り文字として、コンマまたは改行を使用できます。

識別子 | 意味 | 構造
--- | --- | ---
d | dict | 辞書
o | ordered dict | 順序付き辞書

```
d = ["one": 1, "two": 2]
t = [
    "red": "aka"
    "blue": "ao"
]
```

### テーブル

`[foo = 0, bar = 1]`のようにテーブルを表現できます。  
特に空のテーブルを表現するとき、リテラルの直前に一文字の識別子`T`を
付加してください。  
区切り文字として、コンマまたは改行を使用できます。

テーブルは辞書に似ていますが、キーとして文字列だけを使用します。  
値へのアクセスには要素アクセス`table.key`を使用します。  
予約されたキー`metatable`に他のテーブルを対応させることで、
アクセスが失敗した時そのテーブルを探索させることができます。  
また、`get_`, `set_`で始まるキーが存在するとき、それに関連付けられた関数を
自動的にゲッター、セッターとして使用します。

また、テーブルの要素としてテーブルを追加したとき、追加された側のテーブルは
キー`parent`に対応させて、親のテーブルを記憶します。

```
Circle = [
    get_diameter = {current.radius * 2}
    area = {
        return 3.14 * current.radius pow 2
    }
    cylinder = {tall ->
        return tall * @area()
    }
]

circle0 = [
    metatable = Circle
    radius = 10
]

print(circle0.diameter)
print(circle0.cylinder(10))
```

### 関数

`{foo=d0, bar~=d1, baz -> return baz}`または`{baz}`のように関数を表現できます。  
引数にデフォルト値を設定するための演算子として`=`, `~=`が使用できます。  
`=`では右辺が関数の定義時に一度だけ評価されるのに対し、`~=`では右辺が関数の実行時に毎回評価されます。  
名前付き引数を持たない場合、矢印記号も省略することができます。  
1番目, 2番目, ...の引数の表現として、`%0`, `%1`, ...を用いることができます。  

実行したときの返り値は関数中のreturn文で決定しますが、
return文が省略されれば最後に評価された値が返り値となります。  
現行の実装では誤った数の引数が与えられたり、存在しないキーワード引数が与えられても、エラーを送出しません。

テーブルの要素である関数が呼び出されたとき、テーブルが予約されたキーワード引数`current`として渡されます。
詳しくは要素アクセス演算子の項を参照してください。

```
f = {x=[1], y~=[1] ->
    x.append(0)
    y.append(0)
    print(x)
    print(y)
}
f()
f()

g = {foo, bar=30, baz=20 -> foo + bar + baz}

print(g(1))
print(g(2, 3))
print(g(2, baz=5))

h = {%0 pow %1}
print(h(2, 2))
```

### 記号エイリアス

`current`に対して`@`、`parent`に対して`^`をエイリアスとして使用できます。  
また、記号と記号の間、および記号と英数字の間の要素アクセス演算子`.`は省略できます。

```
t = [
    v1 = 100
    c = [
        v2 = 200
        f = {print(@v2, @^v1}
    ]
]

t.c.f()
```

### 内包表記

シーケンス・マッピングの内包表記が使用できます。
多重代入が可能であるほか、`i for i`は`i`に省略可能です。

```
a = [i * 2 for i in 3..9]
b = [k: v!'foo' for k, v in bar.items()]
c = [i in foo if i mod 2 == 0]
```

## 3.演算子

優先度の高い順に取り上げます。  
一般的なプログラミング言語と同様に、括弧でくくることで優先順位を操作できます。

### 範囲

`A..B`で範囲[a, b]に、`A..<B`で範囲[a, b)になります。Pythonのrange関数で得られるものと同じです。  

```
for i in 1..10:
    print(i)
:

l = [1, 2, 3, 4, 5]
print(l[1..2])
```

### 要素アクセス・インデックスアクセス・関数呼び出し

要素アクセスは`foo.bar`のように行います。ここで左辺がテーブル、右辺が関数の場合、右辺の関数に
予約されたキーワード引数`current`として左辺が渡されます。

インデックスアクセスは`foo!0`のように行います。`!`の優先度は高いので、
`foo ! 2 * 3`は`(foo ! 2) * 3`と解釈されます。従って、代替表現`foo(! 2 * 3)`を用いてください。

関数呼び出しはPythonと同様に`foo(bar)`のように行います。キーワード引数を用いることもできます。
現行の実装ではシーケンスやマッピングのアンパックはできません。

```
foo().bar(!'baz')(!10).piyo = puyo!'hoge'
```

### べき乗

`A pow B`です。

### 正負

`+A`, `-B`です。

### 乗除・剰余

`A * B`, `A / B`, `A mod B`です。

### 加減

`A + B`, `A - B`です。

### 比較

`A < B`, `A <= B`, `A == B`, `A != B`, `A >= B`, `A > B`です。

### 同一・包含・クラスの同一性

`A is B`, `A in B`, `A isa B`です。`A isa B`は`isinstance(A, B)`と同じです。
現行の実装ではnot inは実装していません。

### 否定

`not A`です。

### 論理積・論理和

`A and B`, `A or B`です。

### if式

`A if C else B`です。Pythonと同じです。

### except式

`A except E then B`です。まずAを返そうとしますが、Aの評価中にエラーEを捕捉した場合にBを返します。

## 4. 制御構造

### if文

Pythonと似ていますが、elseifを用いることと、最後のセミコロンに注意してください。

```
if C1:
    B1
elseif C2:
    B2
else:
    B3
;
```

### while文

```
while C:
    B
;
```

### for文

ここでも多重代入が可能です。

```
for foo in bar:
    print(foo)
;

for foo, bar in baz:
    print(foo * bar)
;
```

### times文

指定回数だけループします。

```
times 100:
    print("This is so important thing that I say 100 times.")
;

times inf:
    print("It may be more readable than \"while true.\"")
;
```

### continue, break, return文

breakに続けて数値を与えると、ループを抜ける回数を指定できます。

```
while true:
    while true:
        if foo:
            continue
        else:
            break 2
        ;
    ;
;

f = {
    return -1
    print("Do not show.")
}
print(f())
```

### try文・raise文

```
try:
    raise SomeError
except SomeError:
    print("Error caught.")
;
```

### assert文

単独で用いると無条件にAssertionErrorを送出します。

```
assert 1 + 1 == 2
assert
```

## 5. その他

### ビルトイン定数

Pythonと異なり、小文字で始まります。

定数 | 値
--- | ---
true | 真
false | 偽
none | NULL値
inf | 無限大
py | builtinsモジュール
op | operatorモジュール
__lagoonfile__ | 実行中のファイルのパス

### ビルトイン関数

関数 | 機能
--- | ---
import | Pythonのimport文と同じ。文字列を引数に取り、モジュールを返す。
importall | importと似ているが、モジュール中の関数を現在の名前空間に取り込む。
load | Lagoonファイルのパス文字列を引数に取り、実行する。実行後の名前空間を返す。
loadall | loadと似ているが、実行後の名前空間を現在の名前空間に取り込む。
assert | 引数が偽のときAssertionErrorを送出する。
exec | Lagoonコードを実行する。
eval | Lagoonコードを評価する。

この他、Pythonのビルトイン関数のいくつかを同名または別名で定義しています。
詳しくはソースコードを参照してください。
