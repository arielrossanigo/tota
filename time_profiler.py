# -*- coding: utf-8 -*-
#from __future__ import division
from datetime import datetime
from collections import defaultdict


class Timer(defaultdict):

    def __init__(self):
        super(Timer, self).__init__(list)
        self.line = '| {:%d}| {:15.2f}| {:12.2f}| {:11d}|'

    def header(self, width):
        return (('| {:%d}| {:15}| {:12}| {:11}|' % width).
                format('Function', 'Total time (s)', 'AVG time (s)', 'Calls'))

    def stats(self, functions=None, reset_counters=False):
        if functions is None:
            functions = self.keys()

        if len(functions) == 0:
            return ''

        width = max([len(f) for f in functions]) + 1
        lines = []
        for f in functions:
            times = self[f]
            total_time = sum(times)
            calls = len(times)
            if calls > 0:
                avg_time = total_time / calls
            else:
                avg_time = 0
            lines.append(
                (total_time,
                 (self.line % width).format(f, total_time, avg_time, calls)))
            if reset_counters:
                self[f] = []

        lines.sort(reverse=True)
        lines = [x[1] for x in lines]
        lines.insert(0, self.header(width))
        return '\n'.join(lines)


def profile_time(timer):
    def decorator(function):
        def inner(*args, **kwargs):
            start_time = datetime.now()
            result = function(*args, **kwargs)
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            timer[function.__qualname__].append(elapsed)
            return result
        return inner
    return decorator

timer = Timer()


@profile_time(timer)
def f1(x):
    acc = 0
    for i in range(100000):
        acc += x
    return acc


@profile_time(timer)
def f2(x):
    acc = 0
    for i in range(100000):
        acc += x
    return acc

if __name__ == '__main__':
    for i in range(1000):
        f1(10)

    for i in range(100):
        f2(10)

    timer.stats()
