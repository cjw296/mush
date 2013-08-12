from unittest import TestCase

from mock import Mock, call
from testfixtures import ShouldRaise, compare

from mush import Runner, requires, first, last, attr, item

class RunnerTests(TestCase):

    def test_simple_chain(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass
        t1 = T1()
        t2 = T2()
        
        def parser():
            m.parser()
            return t1

        @requires(T1)
        def base_args(obj):
            m.base_args(obj)

        @requires(last(T1))
        def parse(obj):
            m.parse(obj)
            return t2

        runner = Runner(parser, base_args, parse)
        
        @requires(T1)
        def my_args(obj):
            m.my_args(obj)

        runner.add(my_args)
        
        @requires(T2)
        def job(obj):
            m.job(obj)

        runner.add(job)

        runner()
        
        compare([
                call.parser(),
                call.base_args(t1),
                call.my_args(t1),
                call.parse(t1),
                call.job(t2),
                ], m.mock_calls)

    def test_circular(self):
        class T1(object): pass
        class T2(object): pass
        class T3(object): pass

        def f1(): return T1()
        def f2(t1, t3): return T2()
        def f3(t2): return T3()

        runner = Runner()
        runner.add(f1)
        runner.add(f2, T1, T3)
        runner.add(f3, T2)

        with ShouldRaise(KeyError(
                "'No T3 in context' attempting to call "+repr(f2)
                )):
            runner()

    def test_complex_(self):
        # parser -> args -> dbs (later) -> job (earlier)
        m = Mock()
        class T1(object): pass
        class T2(object): pass
        class T3(object): pass

        def parser():
            m.parser()
            return T1()

        @requires(T1)
        def args(obj):
            m.args(type(obj))
        
        @requires(T2)
        def dbs(obj):
            m.dbs(type(obj))
            return T3()
        
        @requires(last(T1))
        def parse(obj):
            m.parse(type(obj))
            return T2()

        runner = Runner(parser, args, dbs, parse)
        
        @requires(T1)
        def more_args(obj):
            m.more_args(type(obj))
        
        @requires(T2, T3)
        def job(o1, o2):
            m.job(type(o1), type(o2))

        runner.add(more_args)
        runner.add(job)
        runner()
        
        compare([
                call.parser(),
                call.args(T1),
                call.more_args(T1),
                call.parse(T1),
                call.dbs(T2),
                call.job(T2, T3),
                ], m.mock_calls)
        
    def test_classes(self):
        m = Mock()        
        class T1(object): pass
        class T2(object): pass
        t1 = T1()
        t2 = T2()
        
        class Base(object):

            def parser(self):
                m.Base.parser()
                return t1

            @requires(T1)
            def args(self, obj):
                m.Base.args(obj)

            @requires(last(T1))
            def parse(self, obj):
                m.Base.parse(obj)
                return t2


        class Actual(object):

            @requires(T1)
            def args(self, obj):
                m.Actual.args(obj)

            @requires(T2)
            def __call__(self, obj):
                m.Actual.call(obj)

        runner = Runner(Base, Base.parser, Base.args, Base.parse,
                        Actual, Actual.args, Actual.__call__)
        runner()
        
        compare([
                call.Base.parser(),
                call.Base.args(t1),
                call.Actual.args(t1),
                call.Base.parse(t1),
                call.Actual.call(t2),
                ], m.mock_calls)

    def test_ordering(self):
        m = Mock()
        class Type(): pass

        @requires(first())
        def f_none(): m.f_none()
        def n_none(): m.n_none()
        @requires(last())
        def l_none(): m.l_none()
        def make_t(): return Type()

        @requires(first(Type))
        def f_t(t): m.f_t()
        @requires(Type)
        def n_t(t): m.n_t()
        @requires(last(Type))
        def l_t(t): m.l_t()
        
        Runner(l_t, n_t, l_none, f_t, f_none, n_none, make_t)()
        
        compare([
                call.f_none(),
                call.n_none(),
                call.l_none(),
                call.f_t(),
                call.n_t(),
                call.l_t(),
                ], m.mock_calls)

    def test_when_how(self):
        m = Mock()
        class T(dict):
            foo = 'bar'
        @requires(first(attr(T, 'foo')))
        def f_t(o): m.f_t(o)
        @requires(T)
        def n_t(o): m.n_t(o.__class__)
        @requires(last(item(T, 'baz')))
        def l_t(o): m.l_t(o)

        def make_t():
            t = T()
            t['baz'] = 'bob'
            return t

        Runner(l_t, n_t, f_t, make_t)()

        compare([
                call.f_t('bar'),
                call.n_t(T),
                call.l_t('bob'),
                ], m.mock_calls)

    def test_how_when(self):
        m = Mock()
        class T(dict):
            foo = 'bar'
        @requires(item(first(T), 'baz'))
        def f_t(o): m.f_t(o)
        @requires(T)
        def n_t(o): m.n_t(o.__class__)
        @requires(attr(last(T), 'foo'))
        def l_t(o): m.l_t(o)

        def make_t():
            t = T()
            t['baz'] = 'bob'
            return t

        Runner(l_t, n_t, f_t, make_t)()

        compare([
                call.f_t('bob'),
                call.n_t(T),
                call.l_t('bar'),
                ], m.mock_calls)
    
