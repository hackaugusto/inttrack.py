'''
Helper to track integer operations.

>>> track(5) * 2 - 3
7
>>> (track(5) * 2 - 3).operations
sub(lhs=mul(lhs=5, rhs=2), rhs=3)
>>> expression((track(5) * 2 - 3).operations)
'((5 * 2) - 3)'
'''
import operator
import unittest
import sys

from collections import namedtuple
from decimal import Decimal
from functools import partial as _partial

abs = namedtuple('abs', ('lhs'))
neg = namedtuple('neg', ('lhs'))

add = namedtuple('add', ('lhs', 'rhs'))
div = namedtuple('div', ('lhs', 'rhs'))
mod = namedtuple('mod', ('lhs', 'rhs'))
mul = namedtuple('mul', ('lhs', 'rhs'))
sub = namedtuple('sub', ('lhs', 'rhs'))


op_format = {
    'abs': 'abs({})',
    'neg': '-{}',

    'add': '{} + {}',
    'div': '{} / {}',
    'mod': '{} % {}',
    'mul': '{} * {}',
    'sub': '{} - {}',
}


def track(number):
    if isinstance(number, Decimal):
        return DecimalTrack(number)
    return IntTrack(number)


def partial(function, *args, **kwargs):
    ''' add __get__ to python's partial implementation '''
    function = _partial(function, *args, **kwargs)

    # if this function is used as a property it will bind self as the first
    # argument in *args, otherwise it can be used as a normal function
    def bind(*args, **kwargs):
        return function(*args, **kwargs)

    return bind


def unary_op(type_, operator, operation, lhs):
    if hasattr(lhs, 'operations') and lhs.operations is not None:
        lhs_operations = lhs.operations
    else:
        lhs_operations = lhs

    result = operator(type_(lhs))
    return IntTrack(result, operation(lhs_operations))


def binary_op(type_, operator, operation, lhs, rhs):
    if hasattr(lhs, 'operations') and lhs.operations is not None:
        lhs_operations = lhs.operations
    else:
        lhs_operations = lhs

    if hasattr(rhs, 'operations') and rhs.operations is not None:
        rhs_operations = rhs.operations
    else:
        rhs_operations = rhs

    result = operator(type_(lhs), type_(rhs))
    return IntTrack(result, operation(lhs_operations, rhs_operations))


def binary_rop(type_, operator, operation, rhs, lhs):
    return binary_op(type_, operator, operation, lhs, rhs)


def expression(operations, callback=None):
    '''Create a readable string from operations, use callback to change the numeric values'''
    if not isinstance(operations, tuple):
        if callback:
            return str(callback(operations))
        return str(operations)

    subexpressions = (expression(op, callback) for op in operations)
    return '({})'.format(op_format[operations.__class__.__name__].format(*subexpressions))


class IntTrack(int):
    def __new__(cls, value, operations=None):
        obj = super(IntTrack, cls).__new__(cls, value)
        obj.operations = operations
        return obj

    __abs__ = partial(unary_op, int, operator.abs, abs)
    __neg__ = partial(unary_op, int, operator.neg, neg)

    __add__ = partial(binary_op, int, operator.add, add)
    __mod__ = partial(binary_op, int, operator.mod, mod)
    __mul__ = partial(binary_op, int, operator.mul, mul)
    __sub__ = partial(binary_op, int, operator.sub, sub)
    __truediv__ = partial(binary_op, int, operator.truediv, div)

    __radd__ = partial(binary_rop, int, operator.add, add)
    __rmod__ = partial(binary_rop, int, operator.mod, mod)
    __rmul__ = partial(binary_rop, int, operator.mul, mul)
    __rsub__ = partial(binary_rop, int, operator.sub, sub)
    __rtruediv__ = partial(binary_rop, int, operator.truediv, div)

    if sys.version_info[0] == 2:
        __div__ = partial(binary_op, int, operator.div, div)
        __rdiv__ = partial(binary_rop, int, operator.div, div)


class DecimalTrack(Decimal):
    # Decimal has __init__ on 2.7 but does on 3.4
    def __new__(cls, value, operations=None):
        obj = super(DecimalTrack, cls).__new__(cls, value)
        obj.operations = operations
        return obj

    __abs__ = partial(unary_op, Decimal, operator.abs, abs)
    __neg__ = partial(unary_op, Decimal, operator.neg, neg)

    __add__ = partial(binary_op, Decimal, operator.add, add)
    __mod__ = partial(binary_op, Decimal, operator.mod, mod)
    __mul__ = partial(binary_op, Decimal, operator.mul, mul)
    __sub__ = partial(binary_op, Decimal, operator.sub, sub)
    __truediv__ = partial(binary_op, Decimal, operator.truediv, div)

    __radd__ = partial(binary_rop, Decimal, operator.add, add)
    __rmod__ = partial(binary_rop, Decimal, operator.mod, mod)
    __rmul__ = partial(binary_rop, Decimal, operator.mul, mul)
    __rsub__ = partial(binary_rop, Decimal, operator.sub, sub)
    __rtruediv__ = partial(binary_op, Decimal, operator.truediv, div)

    if sys.version_info[0] == 2:
        __div__ = partial(binary_op, Decimal, operator.div, div)
        __rdiv__ = partial(binary_rop, Decimal, operator.div, div)


class TrackTestCase(unittest.TestCase):
    def test_unaryop(self):
        self.assertEquals(-track(5), -5)
        self.assertEquals((-track(5)).operations, neg(5))

        self.assertEquals(operator.abs(track(-5)).operations, abs(-5))

    def test_binaryop(self):
        result = binary_op(int, operator.mul, mul, 5, 3)
        self.assertEquals(result, 15)
        self.assertEquals(result.operations, mul(5, 3))

        result = binary_op(int, operator.add, add, result, result)
        self.assertEquals(result.operations, add(mul(5, 3), mul(5, 3)))

    def test_partial(self):
        opmul = partial(binary_op, int, operator.mul, mul)

        self.assertEquals(opmul(5, 3), binary_op(int, operator.mul, mul, 5, 3))
        self.assertEquals(opmul.__get__(5)(3), binary_op(int, operator.mul, mul, 5, 3))

    def test_decimal(self):
        self.assertEquals(-track(Decimal(5)), -5)
        self.assertEquals((-track(Decimal(5))).operations, neg(5))

        self.assertEquals(operator.abs(track(Decimal(-5))).operations, abs(-5))

        result = binary_op(Decimal, operator.mul, mul, 5, 3)
        self.assertEquals(result, 15)
        self.assertEquals(result.operations, mul(5, 3))

        result = binary_op(Decimal, operator.add, add, result, result)
        self.assertEquals(result.operations, add(mul(5, 3), mul(5, 3)))

    def test_partial_binding(self):
        def binding(value, self):
            return value, self

        self.assertEquals(partial(binding, 5).__get__(3)(), (5, 3))

    def test_order(self):
        self.assertEquals((4 * track(5)).operations, mul(4, 5))
        self.assertEquals((track(7) / 3).operations, div(7, 3))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', default=False, help='flag to run the tests')
    parser.add_argument('--failfast', action='store_true', default=False, help='unittest failfast')
    args = parser.parse_args()

    if args.test:
        import doctest

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TrackTestCase)
        result = unittest.TextTestRunner(failfast=args.failfast).run(suite)

        if result.errors or result.failures:
            sys.exit(len(result.errors) + len(result.failures))

        (failures, total) = doctest.testmod()

        if failures:
            sys.exit(failures)
