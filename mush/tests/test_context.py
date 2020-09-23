# from typing import Tuple, List
#
from testfixtures import ShouldRaise, compare
# from testfixtures.mock import Mock
#
from mush import (
    Context#, requires, returns, returns_mapping, Value, missing
)
from mush.context import ResourceError
# from mush.declarations import RequiresType, requires_nothing, returns_nothing
# from mush.requirements import Requirement
from .helpers import TheType
from ..resources import Resource


class TestContext(object):

    def test_add_by_inferred_type(self):
        obj = TheType()
        context = Context()
        context.add(obj)

        compare(context._store, expected={(TheType, None): Resource(obj)})
        expected = (
            "<Context: {\n"
            "    <class 'mush.tests.helpers.TheType'>: <TheType obj>\n"
            "}>"
        )
        compare(expected, actual=repr(context))
        compare(expected, actual=str(context))

    def test_add_by_identifier(self):
        obj = TheType()
        context = Context()
        context.add(obj, identifier='my label')

        compare(context._store, expected={
            (TheType, 'my label'): Resource(obj),
            (None, 'my label'): Resource(obj),
        })
        expected = ("<Context: {\n"
                    "    <class 'mush.tests.helpers.TheType'>, 'my label': <TheType obj>\n"
                    "    'my label': <TheType obj>\n"
                    "}>")
        compare(expected, actual=repr(context))
        compare(expected, actual=str(context))

    def test_add_by_identifier_only(self):
        obj = TheType()
        context = Context()
        context.add(obj, provides=None, identifier='my label')

        compare(context._store, expected={(None, 'my label'): Resource(obj)})
        expected = ("<Context: {\n"
                    "    'my label': <TheType obj>\n"
                    "}>")
        compare(expected, actual=repr(context))
        compare(expected, actual=str(context))

    def test_explicit_type(self):
        class T2(object): pass
        obj = TheType()
        context = Context()
        context.add(obj, provides=T2)
        compare(context._store, expected={(T2, None): Resource(obj)})
        expected = ("<Context: {\n"
                    "    " + repr(T2) + ": <TheType obj>\n"
                    "}>")
        compare(expected, actual=repr(context))
        compare(expected, actual=str(context))

    def test_clash_just_type(self):
        obj1 = TheType()
        obj2 = TheType()
        context = Context()
        context.add(obj1, TheType)
        with ShouldRaise(ResourceError(f'Context already contains {TheType!r}')):
            context.add(obj2, TheType)

    def test_clash_just_identifier(self):
        obj1 = TheType()
        obj2 = TheType()
        context = Context()
        context.add(obj1, provides=None, identifier='my label')
        with ShouldRaise(ResourceError("Context already contains 'my label'")):
            context.add(obj2, provides=None, identifier='my label')

    def test_clash_identifier_only_with_identifier_plus_type(self):
        obj1 = TheType()
        obj2 = TheType()
        context = Context()
        context.add(obj1, provides=None, identifier='my label')
        with ShouldRaise(ResourceError("Context already contains 'my label'")):
            context.add(obj2, identifier='my label')

    def test_clash_identifier_plus_type_with_identifier_only(self):
        obj1 = TheType()
        obj2 = TheType()
        context = Context()
        context.add(obj1, identifier='my label')
        with ShouldRaise(ResourceError("Context already contains 'my label'")):
            context.add(obj2, provides=None, identifier='my label')

    def test_call_no_params(self):
        def foo():
            return 'bar'
        context = Context()
        result = context.call(foo)
        compare(result, 'bar')

    def test_call_type_from_annotation(self):
        def foo(baz: str):
            return baz
        context = Context()
        context.add('bar')
        result = context.call(foo)
        compare(result, expected='bar')

    def test_call_identifier_from_annotation(self):
        def foo(baz: str):
            return baz
        context = Context()
        context.add('bar', provides=str)
        context.add('bob', identifier='baz')
        result = context.call(foo)
        compare(result, expected='bob')

    def test_call_by_identifier_only(self):
        def foo(param):
            return param

        context = Context()
        context.add('bar', identifier='param')
        result = context.call(foo)
        compare(result, 'bar')

    def test_call_requires_missing(self):
        def foo(obj: TheType): return obj
        context = Context()
        with ShouldRaise(ResourceError(
            "Value(<class 'mush.tests.helpers.TheType'>, 'obj') could not be satisfied"
        )):
            context.call(foo)

    def test_call_optional_type_present(self):
        def foo(x: TheType = 1):
            return x
        context = Context()
        context.add(2, TheType)
        result = context.call(foo)
        compare(result, 2)

    def test_call_optional_type_missing(self):
        def foo(x: TheType = 1):
            return x
        context = Context()
        result = context.call(foo)
        compare(result, 1)

    def test_call_optional_identifier_present(self):
        def foo(x=1):
            return x

        context = Context()
        context.add(2, identifier='x')
        result = context.call(foo)
        compare(result, 2)

    def test_call_optional_identifier_missing(self):
        def foo(x=1):
            return x

        context = Context()
        context.add(2)
        result = context.call(foo)
        compare(result, 1)

    def test_call_requires_context(self):
        context = Context()

        def return_context(context_: Context):
            return context_

        assert context.call(return_context) is context

    def test_call_requires_requirement(self):
        # this should blow up unless we're in a provider?
        pass

# XXX - these are for explicit requires() objects:
    # def test_call_requires_string(self):
    #     def foo(obj):
    #         return obj
    #     context = Context()
    #     context.add('bar', identifier='baz')
    #     result = context.call(foo, requires('baz'))
    #     compare(result, expected='bar')
    #     compare({'baz': 'bar'}, actual=context._store)

#     def test_call_requires_type(self):
#         def foo(obj):
#             return obj
#         context = Context()
#         context.add('bar', TheType)
#         result = context.call(foo, requires(TheType))
#         compare(result, 'bar')
#         compare({TheType: 'bar'}, actual=context._store)
#
    #
    #     def test_call_requires_accidental_tuple(self):
    #         def foo(obj): return obj
    #         context = Context()
    #         with ShouldRaise(TypeError(
    #                 "(<class 'mush.tests.helpers.TheType'>, "
    #                 "<class 'mush.tests.helpers.TheType'>) "
    #                 "is not a valid decoration type"
    #         )):
    #             context.call(foo, requires((TheType, TheType)))
#
#     def test_call_requires_optional_override_source_and_default(self):
#         def foo(x=1):
#             return x
#         context = Context()
#         context.add(2, provides='x')
#         result = context.call(foo, requires(x=Value('y', default=3)))
#         compare(result, expected=3)
#


# XXX - these are for ops
#     def test_call_requires_item_missing(self):
#         def foo(obj): return obj
#         context = Context()
#         context.add({}, TheType)
#         with ShouldRaise(ResourceError(
#             "No Value(TheType)['foo'] in context",
#             key=TheType,
#             requirement=Value(TheType)['foo'],
#         )):
#             context.call(foo, requires(Value(TheType)['foo']))
#
#     def test_call_requires_named_parameter(self):
#         def foo(x, y):
#             return x, y
#         context = Context()
#         context.add('foo', TheType)
#         context.add('bar', 'baz')
#         result = context.call(foo, requires(y='baz', x=TheType))
#         compare(result, ('foo', 'bar'))
#         compare({TheType: 'foo',
#                  'baz': 'bar'},
#                 actual=context._store)
#
#     def test_call_requires_item(self):
#         def foo(x):
#             return x
#         context = Context()
#         context.add(dict(bar='baz'), 'foo')
#         result = context.call(foo, requires(Value('foo')['bar']))
#         compare(result, 'baz')
#
#     def test_call_requires_attr(self):
#         def foo(x):
#             return x
#         m = Mock()
#         context = Context()
#         context.add(m, 'foo')
#         result = context.call(foo, requires(Value('foo').bar))
#         compare(result, m.bar)
#
#     def test_call_requires_item_attr(self):
#         def foo(x):
#             return x
#         m = Mock()
#         m.bar= dict(baz='bob')
#         context = Context()
#         context.add(m, provides='foo')
#         result = context.call(foo, requires(Value('foo').bar['baz']))
#         compare(result, 'bob')
#
#     def test_call_requires_optional_item_missing(self):
#         def foo(x: str = Value('foo', default=1)['bar']):
#             return x
#         context = Context()
#         result = context.call(foo)
#         compare(result, 1)
#
#     def test_call_requires_optional_item_present(self):
#         def foo(x: str = Value('foo', default=1)['bar']):
#             return x
#         context = Context()
#         context.add(dict(bar='baz'), provides='foo')
#         result = context.call(foo)
#         compare(result, 'baz')


# XXX requirements caching:
#
#     def test_call_caches_requires(self):
#         context = Context()
#         def foo(): pass
#         context.call(foo)
#         compare(context._requires_cache[foo], expected=RequiresType())
#
#     def test_call_explict_explicit_requires_no_cache(self):
#         context = Context()
#         context.add('a')
#         def foo(*args):
#             return args
#         result = context.call(foo, requires(str))
#         compare(result, ('a',))
#         compare(context._requires_cache, expected={})
#
#     def test_extract_minimal(self):
#         o = TheType()
#         def foo() -> TheType:
#             return o
#         context = Context()
#         result = context.extract(foo)
#         assert result is o
#         compare({TheType: o}, actual=context._store)
#         compare(context._requires_cache[foo], expected=RequiresType())
#         compare(context._returns_cache[foo], expected=returns(TheType))
#
#     def test_extract_maximal(self):
#         def foo(*args):
#             return args
#         context = Context()
#         context.add('a')
#         result = context.extract(foo, requires(str), returns(Tuple[str]))
#         compare(result, expected=('a',))
#         compare({
#             str: 'a',
#             Tuple[str]: ('a',),
#         }, actual=context._store)
#         compare(context._requires_cache, expected={})
#         compare(context._returns_cache, expected={})
#
#     def test_returns_single(self):
#         def foo():
#             return 'bar'
#         context = Context()
#         result = context.extract(foo, requires_nothing, returns(TheType))
#         compare(result, 'bar')
#         compare({TheType: 'bar'}, actual=context._store)
#
#     def test_returns_sequence(self):
#         def foo():
#             return 1, 2
#         context = Context()
#         result = context.extract(foo, requires_nothing, returns('foo', 'bar'))
#         compare(result, (1, 2))
#         compare({'foo': 1, 'bar': 2},
#                 actual=context._store)
#
#     def test_returns_mapping(self):
#         def foo():
#             return {'foo': 1, 'bar': 2}
#         context = Context()
#         result = context.extract(foo, requires_nothing, returns_mapping())
#         compare(result, {'foo': 1, 'bar': 2})
#         compare({'foo': 1, 'bar': 2},
#                 actual=context._store)
#
#     def test_ignore_return(self):
#         def foo():
#             return 'bar'
#         context = Context()
#         result = context.extract(foo, requires_nothing, returns_nothing)
#         compare(result, 'bar')
#         compare({}, context._store)
#
#     def test_ignore_non_iterable_return(self):
#         def foo(): pass
#         context = Context()
#         result = context.extract(foo)
#         compare(result, expected=None)
#         compare(context._store, expected={})
#
#     def test_remove(self):
#         context = Context()
#         context.add('foo')
#         context.remove(str)
#         compare(context._store, expected={})
#
#     def test_remove_not_there_strict(self):
#         context = Context()
#         with ShouldRaise(ResourceError("Context does not contain 'foo'",
#                                        key='foo')):
#             context.remove('foo')
#         compare(context._store, expected={})
#
#     def test_remove_not_there_not_strict(self):
#         context = Context()
#         context.remove('foo', strict=False)
#         compare(context._store, expected={})
#
#     def test_nest(self):
#         c1 = Context()
#         c1.add('a', provides='a')
#         c1.add('c', provides='c')
#         c2 = c1.nest()
#         c2.add('b', provides='b')
#         c2.add('d', provides='c')
#         compare(c2.get('a'), expected='a')
#         compare(c2.get('b'), expected='b')
#         compare(c2.get('c'), expected='d')
#         compare(c1.get('a'), expected='a')
#         compare(c1.get('b', default=None), expected=None)
#         compare(c1.get('c'), expected='c')
#
#     def test_nest_with_overridden_default_requirement_type(self):
#         def modifier(): pass
#         c1 = Context(modifier)
#         c2 = c1.nest()
#         assert c2.requirement_modifier is modifier
#
#     def test_nest_with_explicit_default_requirement_type(self):
#         def modifier1(): pass
#         def modifier2(): pass
#         c1 = Context(modifier1)
#         c2 = c1.nest(modifier2)
#         assert c2.requirement_modifier is modifier2
#
#     def test_nest_keeps_declarations_cache(self):
#         c1 = Context()
#         c2 = c1.nest()
#         assert c2._requires_cache is c1._requires_cache
#         assert c2._returns_cache is c1._returns_cache



# XXX "custom requirement" stuff
#
#     def test_custom_requirement(self):
#
#         class FromRequest(Requirement):
#             def resolve(self, context):
#                 return context.get('request')[self.key]
#
#         def foo(bar: FromRequest('bar')):
#             return bar
#
#         context = Context()
#         context.add({'bar': 'foo'}, provides='request')
#         compare(context.call(foo), expected='foo')
#
#     def test_custom_requirement_returns_missing(self):
#
#         class FromRequest(Requirement):
#             def resolve(self, context):
#                 return context.get('request').get(self.key, missing)
#
#         def foo(bar: FromRequest('bar')):
#             pass
#
#         context = Context()
#         context.add({}, provides='request')
#         with ShouldRaise(ResourceError("No FromRequest('bar') in context",
#                                        key='bar',
#                                        requirement=FromRequest.make(key='bar', name='bar'))):
#             compare(context.call(foo))
#
#     def test_default_custom_requirement(self):
#
#         class FromRequest(Requirement):
#             def resolve(self, context):
#                 return context.get('request')[self.key]
#
#         def foo(bar):
#             return bar
#
#         def modifier(requirement):
#             if type(requirement) is Requirement:
#                 requirement = FromRequest.make_from(requirement)
#             return requirement
#
#         context = Context(requirement_modifier=modifier)
#         context.add({'bar': 'foo'}, provides='request')
#         compare(context.call(foo), expected='foo')

    def test_provider(self):
        pass

    def test_provider_needs_requirement(self):
        pass
