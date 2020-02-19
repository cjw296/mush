from collections import deque
from enum import Enum, auto
from functools import (
    WRAPPER_UPDATES,
    WRAPPER_ASSIGNMENTS as FUNCTOOLS_ASSIGNMENTS,
    update_wrapper as functools_update_wrapper,
)
from inspect import signature
from typing import List, Type, Optional, Callable, Sequence, NewType, Union, Any

from .markers import missing


ResourceKey = NewType('ResourceKey', Union[Type, str])
ResourceValue = NewType('ResourceValue', Any)
Resolver = Callable[['Context', Any], ResourceValue]


def name_or_repr(obj):
    return getattr(obj, '__name__', None) or repr(obj)


def set_mush(obj, key, value):
    if not hasattr(obj, '__mush__'):
        obj.__mush__ = {}
    obj.__mush__[key] = value


class Requirement:

    def __init__(self, source, target=None):
        self.target = target
        self.spec = source
        self.ops = deque()
        while isinstance(source, how):
            self.ops.appendleft(source.process)
            source = source.type
        self.key: ResourceKey = source

    def __repr__(self):
        requirement_repr = name_or_repr(self.spec)
        if self.target is None:
            return requirement_repr
        else:
            return f'{self.target}={requirement_repr}'


class RequiresType(list):
    """
    Represents requirements for a particular callable.

    The passed in `args` and `kw` should map to the types, including
    any required :class:`~.declarations.how`, for the matching
    arguments or keyword parameters the callable requires.

    String names for resources must be used instead of types where the callable
    returning those resources is configured to return the named resource.
    """

    def __init__(self, *args, **kw):
        super(requires, self).__init__()
        check_type(*args)
        check_type(*kw.values())
        self.resolvers = []
        for arg in args:
            self.append(Requirement(arg))
        for k, v in kw.items():
            self.append(Requirement(v, target=k))

    def __repr__(self):
        return f"requires({', '.join(repr(r) for r in self)})"

    def __call__(self, obj):
        set_mush(obj, 'requires', self)
        return obj


requires = RequiresType


class ReturnsType(object):

    def __call__(self, obj):
        set_mush(obj, 'returns', self)
        return obj

    def __repr__(self):
        return self.__class__.__name__ + '()'


class returns_result_type(ReturnsType):
    """
    Default declaration that indicates a callable's return value
    should be used as a resource based on the type of the object returned.

    ``None`` is ignored as a return value.
    """

    def process(self, obj):
        if obj is not None:
            yield obj.__class__, obj


class returns_mapping(ReturnsType):
    """
    Declaration that indicates a callable returns a mapping of type or name
    to resource.
    """

    def process(self, mapping):
        return mapping.items()


class returns_sequence(returns_result_type):
    """
    Declaration that indicates a callable's returns a sequence of values
    that should be used as a resources based on the type of the object returned.

    Any ``None`` values in the sequence are ignored.
    """

    def process(self, sequence):
        super_process = super(returns_sequence, self).process
        for obj in sequence:
            for pair in super_process(obj):
                yield pair


class returns(returns_result_type):
    """
    Declaration that specifies names for returned resources or overrides
    the type of a returned resource.

    This declaration can be used to indicate the type or name of a single
    returned resource or, if multiple arguments are passed, that the callable
    will return a sequence of values where each one should be named or have its
    type overridden.
    """

    def __init__(self, *args):
        check_type(*args)
        self.args = args

    def process(self, obj):
        if len(self.args) == 1:
            yield self.args[0], obj
        else:
            for t, o in zip(self.args, obj):
                yield t, o

    def __repr__(self):
        args_repr = ', '.join(name_or_repr(arg) for arg in self.args)
        return self.__class__.__name__ + '(' + args_repr + ')'


class DeclarationsFrom(Enum):
    #: Use declarations from the original callable.
    original = auto()
    #: Use declarations from the replacement callable.
    replacement = auto()


original = DeclarationsFrom.original
replacement = DeclarationsFrom.replacement


class how(object):
    """
    The base class for type decorators that indicate which part of a
    resource is required by a particular callable.

    :param type: The resource type to be decorated.
    :param names: Used to identify the part of the resource to extract.
    """
    type_pattern = '%(type)s'
    name_pattern = ''

    def __init__(self, type, *names):
        check_type(type)
        self.type = type
        self.names = names

    def __repr__(self):
        txt = self.type_pattern % dict(type=name_or_repr(self.type))
        for name in self.names:
            txt += self.name_pattern % dict(name=name)
        return txt

    def process(self, o):
        """
        Extract the required part of the object passed in.
        :obj:`missing` should be returned if the required part
        cannot be extracted.
        :obj:`missing` may be passed in and is usually be handled
        by returning :obj:`missing` immediately.
        """
        return missing

class optional(how):
    """
    A :class:`~.declarations.how` that indicates the callable requires the
    wrapped requirement only if it's present in the :class:`~.context.Context`.
    """
    type_pattern = 'optional(%(type)s)'

    def process(self, o):
        if o is missing:
            return nothing
        return o


class attr(how):
    """
    A :class:`~.declarations.how` that indicates the callable requires the named
    attribute from the decorated type.
    """
    name_pattern = '.%(name)s'

    def process(self, o):
        if o is missing:
            return o
        try:
            for name in self.names:
                o = getattr(o, name)
        except AttributeError:
            return missing
        else:
            return o


class item(how):
    """
    A :class:`~.declarations.how` that indicates the callable requires the named
    item from the decorated type.
    """
    name_pattern = '[%(name)r]'

    def process(self, o):
        if o is missing:
            return o
        try:
            for name in self.names:
                o = o[name]
        except KeyError:
            return missing
        else:
            return o


ok_types = (type, str, how)


def check_type(*objs):
    for obj in objs:
        if not isinstance(obj, ok_types):
            raise TypeError(
                repr(obj)+" is not a type or label"
            )


class Nothing(requires, returns):

    def process(self, result):
        return ()


#: A singleton that be used as a :class:`~mush.requires` to indicate that a
#: callable has no required arguments or as a :class:`~mush.returns` to indicate
#: that anything returned from a callable should be ignored.
nothing = Nothing()

#: A singleton  indicating that a callable's return value should be
#: stored based on the type of that return value.
result_type = returns_result_type()


def maybe_optional(p):
    value = p.name
    if p.default is not p.empty:
        value = optional(value)
    return value


def guess_requirements(obj):
    args = []
    kw = {}
    for name, p in signature(obj).parameters.items():
        if p.kind in {p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD}:
            args.append(maybe_optional(p))
        elif p.kind is p.KEYWORD_ONLY:
            kw[name] = maybe_optional(p)
    if args or kw:
        return requires(*args, **kw)


def extract_requires(obj, explicit=None):
    if explicit is None:
        mush_declarations = getattr(obj, '__mush__', {})
        requires_ = mush_declarations.get('requires', None)
        if requires_ is None:
            annotations = getattr(obj, '__annotations__', None)
            annotations = {} if annotations is None else annotations.copy()
            annotations.pop('return', None)
            requires_ = annotations or None
    else:
        requires_ = explicit

    if isinstance(requires_, requires):
        pass
    elif requires_ is None:
        requires_ = guess_requirements(obj)
    elif isinstance(requires_, (list, tuple)):
        requires_ = requires(*requires_)
    else:
        requires_ = requires(requires_)

    return requires_ or nothing


def extract_returns(obj, explicit=None):
    if explicit is None:
        mush_declarations = getattr(obj, '__mush__', {})
        returns_ = mush_declarations.get('returns', None)
        if returns_ is None:
            annotations = getattr(obj, '__annotations__', {})
            returns_ = annotations.get('return')
    else:
        returns_ = explicit

    if returns_ is None or isinstance(returns_, ReturnsType):
        pass
    elif isinstance(returns_, (list, tuple)):
        returns_ = returns(*returns_)
    else:
        returns_ = returns(returns_)

    return returns_ or result_type


WRAPPER_ASSIGNMENTS = FUNCTOOLS_ASSIGNMENTS + ('__mush__',)


def update_wrapper(wrapper,
                   wrapped,
                   assigned=WRAPPER_ASSIGNMENTS,
                   updated=WRAPPER_UPDATES):
    """
    An extended version of :func:`functools.update_wrapper` that
    also preserves Mush's annotations.
    """
    return functools_update_wrapper(wrapper, wrapped, assigned, updated)
