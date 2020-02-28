from typing import Tuple, List
from unittest import TestCase

from mock import Mock
from mush.context import ResolvableValue
from testfixtures import ShouldRaise, compare

from mush import Context, ContextError, requires, returns, nothing, returns_mapping
from mush.declarations import Requirement, Value, missing, RequiresType


class TheType(object):
    def __repr__(self):
        return '<TheType obj>'


class TestContext(TestCase):

    def test_simple(self):
        obj = TheType()
        context = Context()
        context.add(obj)

        compare(context._store, expected={TheType: ResolvableValue(obj)})
        expected = (
            "<Context: {\n"
            "    <class 'mush.tests.test_context.TheType'>: <TheType obj>\n"
            "}>"
        )
        self.assertEqual(repr(context), expected)
        self.assertEqual(str(context), expected)

    def test_type_as_string(self):
        obj = TheType()
        context = Context()
        context.add(obj, provides='my label')

        expected = ("<Context: {\n"
                    "    'my label': <TheType obj>\n"
                    "}>")
        compare(context._store, expected={'my label': ResolvableValue(obj)})
        self.assertEqual(repr(context), expected)
        self.assertEqual(str(context), expected)

    def test_explicit_type(self):
        class T2(object): pass
        obj = TheType()
        context = Context()
        context.add(obj, provides=T2)
        compare(context._store, expected={T2: ResolvableValue(obj)})
        expected = ("<Context: {\n"
                    "    " + repr(T2) + ": <TheType obj>\n"
                    "}>")
        compare(repr(context), expected)
        compare(str(context), expected)
    
    def test_no_resolver_or_provides(self):
        context = Context()
        with ShouldRaise(ValueError('Cannot add None to context')):
            context.add()
        compare(context._store, expected={})

    def test_resolver_but_no_provides(self):
        context = Context()
        with ShouldRaise(TypeError('Both provides and resolver must be supplied')):
            context.add(resolver=lambda: None)
        compare(context._store, expected={})
    
    def test_resolver(self):
        m = Mock()
        context = Context()
        context.add(provides='foo', resolver=m)
        m.assert_not_called()
        assert context.get('foo') is m.return_value
        m.assert_called_with(context, None)

    def test_resolver_and_resource(self):
        m = Mock()
        context = Context()
        with ShouldRaise(TypeError('resource cannot be supplied when using a resolver')):
            context.add('bar', provides='foo', resolver=m)
        compare(context._store, expected={})

    def test_resolver_with_default(self):
        m = Mock()
        context = Context()
        context.add(provides='foo',
                    resolver=lambda context, default=None: context.get('foo-bar', default))
        assert context.get('foo', default=m) is m

    def test_clash(self):
        obj1 = TheType()
        obj2 = TheType()
        context = Context()
        context.add(obj1, TheType)
        with ShouldRaise(ContextError('Context already contains '+repr(TheType))):
            context.add(obj2, TheType)

    def test_clash_string_type(self):
        obj1 = TheType()
        obj2 = TheType()
        context = Context()
        context.add(obj1, provides='my label')
        with ShouldRaise(ContextError("Context already contains 'my label'")):
            context.add(obj2, provides='my label')

    def test_add_none(self):
        context = Context()
        with ShouldRaise(ValueError('Cannot add None to context')):
            context.add(None, type(None))

    def test_add_none_with_type(self):
        context = Context()
        context.add(None, TheType)
        compare(context._store, expected={TheType: ResolvableValue(None)})

    def test_call_basic(self):
        def foo():
            return 'bar'
        context = Context()
        result = context.call(foo, nothing)
        compare(result, 'bar')

    def test_call_requires_string(self):
        def foo(obj):
            return obj
        context = Context()
        context.add('bar', 'baz')
        result = context.call(foo, requires('baz'))
        compare(result, 'bar')
        compare({'baz': ResolvableValue('bar')}, actual=context._store)

    def test_call_requires_type(self):
        def foo(obj):
            return obj
        context = Context()
        context.add('bar', TheType)
        result = context.call(foo, requires(TheType))
        compare(result, 'bar')
        compare({TheType: ResolvableValue('bar')}, actual=context._store)

    def test_call_requires_missing(self):
        def foo(obj): return obj
        context = Context()
        with ShouldRaise(ContextError(
                "No TheType in context"
        )):
            context.call(foo, requires(TheType))

    def test_call_requires_item_missing(self):
        def foo(obj): return obj
        context = Context()
        context.add({}, TheType)
        with ShouldRaise(ContextError(
                "No Value(TheType)['foo'] in context"
        )):
            context.call(foo, requires(Value(TheType)['foo']))

    def test_call_requires_accidental_tuple(self):
        def foo(obj): return obj
        context = Context()
        with ShouldRaise(TypeError(
                "(<class 'mush.tests.test_context.TheType'>, "
                "<class 'mush.tests.test_context.TheType'>) "
                "is not a valid decoration type"
        )):
            context.call(foo, requires((TheType, TheType)))

    def test_call_requires_named_parameter(self):
        def foo(x, y):
            return x, y
        context = Context()
        context.add('foo', TheType)
        context.add('bar', 'baz')
        result = context.call(foo, requires(y='baz', x=TheType))
        compare(result, ('foo', 'bar'))
        compare({TheType: ResolvableValue('foo'),
                 'baz': ResolvableValue('bar')},
                actual=context._store)

    def test_call_requires_optional_present(self):
        def foo(x=1):
            return x
        context = Context()
        context.add(2, TheType)
        result = context.call(foo, requires(TheType))
        compare(result, 2)
        compare({TheType: ResolvableValue(2)}, actual=context._store)

    def test_call_requires_optional_missing(self):
        def foo(x: TheType = 1):
            return x
        context = Context()
        result = context.call(foo)
        compare(result, 1)

    def test_call_requires_optional_override_source_and_default(self):
        def foo(x=1):
            return x
        context = Context()
        context.add(2, provides='x')
        result = context.call(foo, requires(x=Requirement('y', default=3)))
        compare(result, expected=3)

    def test_call_requires_optional_string(self):
        def foo(x:'foo'=1):
            return x
        context = Context()
        context.add(2, 'foo')
        result = context.call(foo)
        compare(result, 2)
        compare({'foo': ResolvableValue(2)}, actual=context._store)

    def test_call_requires_item(self):
        def foo(x):
            return x
        context = Context()
        context.add(dict(bar='baz'), 'foo')
        result = context.call(foo, requires(Value('foo')['bar']))
        compare(result, 'baz')

    def test_call_requires_attr(self):
        def foo(x):
            return x
        m = Mock()
        context = Context()
        context.add(m, 'foo')
        result = context.call(foo, requires(Value('foo').bar))
        compare(result, m.bar)

    def test_call_requires_item_attr(self):
        def foo(x):
            return x
        m = Mock()
        m.bar= dict(baz='bob')
        context = Context()
        context.add(m, provides='foo')
        result = context.call(foo, requires(Value('foo').bar['baz']))
        compare(result, 'bob')

    def test_call_requires_optional_item_missing(self):
        def foo(x: str = Value('foo', default=1)['bar']):
            return x
        context = Context()
        result = context.call(foo)
        compare(result, 1)

    def test_call_requires_optional_item_present(self):
        def foo(x: str = Value('foo', default=1)['bar']):
            return x
        context = Context()
        context.add(dict(bar='baz'), provides='foo')
        result = context.call(foo)
        compare(result, 'baz')

    def test_call_extract_requirements(self):
        def foo(param):
            return param
        context = Context()
        context.add('bar', 'param')
        result = context.call(foo)
        compare(result, 'bar')

    def test_call_extract_no_requirements(self):
        def foo():
            pass
        context = Context()
        result = context.call(foo)
        compare(result, expected=None)

    def test_call_caches_requires(self):
        context = Context()
        def foo(): pass
        context.call(foo)
        compare(context._requires_cache[foo], expected=RequiresType())

    def test_call_explict_explicit_requires_no_cache(self):
        context = Context()
        context.add('a')
        def foo(*args):
            return args
        result = context.call(foo, requires(str))
        compare(result, ('a',))
        compare(context._requires_cache, expected={})

    def test_extract_minimal(self):
        o = TheType()
        def foo() -> TheType:
            return o
        context = Context()
        result = context.extract(foo)
        assert result is o
        compare({TheType: ResolvableValue(o)}, actual=context._store)
        compare(context._requires_cache[foo], expected=RequiresType())
        compare(context._returns_cache[foo], expected=returns(TheType))

    def test_extract_maximal(self):
        def foo(*args):
            return args
        context = Context()
        context.add('a')
        result = context.extract(foo, requires(str), returns(Tuple[str]))
        compare(result, expected=('a',))
        compare({
            str: ResolvableValue('a'),
            Tuple[str]: ResolvableValue(('a',)),
        }, actual=context._store)
        compare(context._requires_cache, expected={})
        compare(context._returns_cache, expected={})

    def test_returns_single(self):
        def foo():
            return 'bar'
        context = Context()
        result = context.extract(foo, nothing, returns(TheType))
        compare(result, 'bar')
        compare({TheType: ResolvableValue('bar')}, actual=context._store)

    def test_returns_sequence(self):
        def foo():
            return 1, 2
        context = Context()
        result = context.extract(foo, nothing, returns('foo', 'bar'))
        compare(result, (1, 2))
        compare({'foo': ResolvableValue(1), 'bar': ResolvableValue(2)},
                actual=context._store)

    def test_returns_mapping(self):
        def foo():
            return {'foo': 1, 'bar': 2}
        context = Context()
        result = context.extract(foo, nothing, returns_mapping())
        compare(result, {'foo': 1, 'bar': 2})
        compare({'foo': ResolvableValue(1), 'bar': ResolvableValue(2)},
                actual=context._store)

    def test_ignore_return(self):
        def foo():
            return 'bar'
        context = Context()
        result = context.extract(foo, nothing, nothing)
        compare(result, 'bar')
        compare({}, context._store)

    def test_ignore_non_iterable_return(self):
        def foo(): pass
        context = Context()
        result = context.extract(foo, nothing, nothing)
        compare(result, expected=None)
        compare(context._store, expected={})

    def test_context_contains_itself(self):
        context = Context()
        def return_context(context: Context):
            return context
        assert context.call(return_context) is context

    def test_remove(self):
        context = Context()
        context.add('foo')
        context.remove(str)
        compare(context._store, expected={})

    def test_remove_not_there_strict(self):
        context = Context()
        with ShouldRaise(ContextError("Context does not contain 'foo'")):
            context.remove('foo')
        compare(context._store, expected={})

    def test_remove_not_there_not_strict(self):
        context = Context()
        context.remove('foo', strict=False)
        compare(context._store, expected={})

    def test_get_present(self):
        context = Context()
        context.add('bar', provides='foo')
        compare(context.get('foo'), expected='bar')

    def test_get_type(self):
        context = Context()
        context.add(['bar'], provides=List[str])
        compare(context.get(List[str]), expected=['bar'])
        compare(context.get(List[int]), expected=None)
        compare(context.get(List), expected=None)
        # nb: this might be surprising:
        compare(context.get(list), expected=None)

    def test_get_missing(self):
        context = Context()
        compare(context.get('foo'), expected=None)

    def test_nest(self):
        c1 = Context()
        c1.add('a', provides='a')
        c1.add('c', provides='c')
        c2 = c1.nest()
        c2.add('b', provides='b')
        c2.add('d', provides='c')
        compare(c2.get('a'), expected='a')
        compare(c2.get('b'), expected='b')
        compare(c2.get('c'), expected='d')
        compare(c1.get('a'), expected='a')
        compare(c1.get('b'), expected=None)
        compare(c1.get('c'), expected='c')

    def test_nest_with_overridden_default_requirement_type(self):
        class FromRequest(Requirement): pass
        c1 = Context(default_requirement_type=FromRequest)
        c2 = c1.nest()
        assert c2.default_requirement_type is FromRequest

    def test_nest_with_explicit_default_requirement_type(self):
        class Requirement1(Requirement): pass
        class Requirement2(Requirement): pass
        c1 = Context(default_requirement_type=Requirement1)
        c2 = c1.nest(default_requirement_type=Requirement2)
        assert c2.default_requirement_type is Requirement2

    def test_nest_keeps_declarations_cache(self):
        c1 = Context()
        c2 = c1.nest()
        assert c2._requires_cache is c1._requires_cache
        assert c2._returns_cache is c1._returns_cache

    def test_custom_requirement(self):

        class FromRequest(Requirement):
            def resolve(self, context):
                return context.get('request')[self.key]

        def foo(bar: FromRequest('bar')):
            return bar

        context = Context()
        context.add({'bar': 'foo'}, provides='request')
        compare(context.call(foo), expected='foo')

    def test_custom_requirement_returns_missing(self):

        class FromRequest(Requirement):
            def resolve(self, context):
                return context.get('request').get(self.key, missing)

        def foo(bar: FromRequest('bar')):
            pass

        context = Context(default_requirement_type=FromRequest)
        context.add({}, provides='request')
        with ShouldRaise(ContextError("No 'bar' in context")):
            compare(context.call(foo))

    def test_default_custom_requirement(self):

        class FromRequest(Requirement):
            def resolve(self, context):
                return context.get('request')[self.key]

        def foo(bar):
            return bar

        context = Context(default_requirement_type=FromRequest)
        context.add({'bar': 'foo'}, provides='request')
        compare(context.call(foo), expected='foo')
