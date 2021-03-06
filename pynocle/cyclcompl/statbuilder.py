#!/usr/bin/env python
"""
Contains functionality for calculating the Cyclomatic Complexity of python code.  Originally from pygenie (I cannot
find a reliable home base for it), but significantly refactored for clarity and documentation.
"""

import compiler
from compiler.visitor import ASTVisitor

import pynocle.utils as utils

class Stats(object):
    """The base class for other types of statistics.

    name: The name of the method/class/function/file/etc.
    classes: Any classes (or nested classes in the case of a function or class).
    functions: Any functions or methods.
    complexity: The complexity for this object.
    """
    def __init__(self, name):
        self.name = name
        self.classes = []
        self.functions = []
        self.complexity = 1

    def __str__(self):
        return '%s(name=%r, classes=%r, functions=%r, complexity=%r)' % (
            self.__class__.__name__,
            self.name, self.classes, self.functions, self.complexity)

    __repr__ = __str__


class FlatStats(object):
    """Create list of flat stats

       stats in init and flattenStats is of type class Stats
       flatStats is a list of lists with each list containing
       'C/M/F/X', Name, complexity
       summaryStats is a dictionary with keys X/C/M/F/T and value is
       a list of [count, complexity]
    """

    def __init__(self, stats=None):
        self.summaryStats = {'File':[0, 0],
                             'Class':[0, 0],
                             'Method':[0, 0],
                             'Function':[0, 0],
                             'Total':[0, 0]}
        if stats:
            self.flatStats = self.flattenStats(stats)
            self.computeSummary()

    def flattenStats(self, stats):
        def flatten(stats, ns=None):
            if not ns:
                yield 'File', stats.name, stats.complexity
            for s in stats.classes:
                name = '.'.join(filter(None, [ns, s.name]))
                yield 'Class', name, s.complexity
                for x in s.functions:
                    fname = '.'.join([name, x.name])
                    yield 'Method', fname, x.complexity
            for s in stats.functions:
                name = '.'.join(filter(None, [ns, s.name]))
                yield 'Function', name, s.complexity

        return [t for t in flatten(stats)]

    def computeSummary(self):
        for row in self.flatStats:
            self.summaryStats[row[0]][0] += 1
            self.summaryStats['Total'][0] += 1
            self.summaryStats[row[0]][1] = self.summaryStats[row[0]][1] + row[2]
            self.summaryStats['Total'][1] = self.summaryStats['Total'][1] + row[2]


class CCVisitor(ASTVisitor):
    """Encapsulates the cyclomatic complexity counting."""
    def __init__(self, ast):
        ASTVisitor.__init__(self)
        if isinstance(ast, basestring):
            ast = compiler.parse(ast)

        self.stats = Stats(ast.name)
        for child in ast.getChildNodes():
            compiler.walk(child, self, walker=self)

    def dispatchChildren(self, node):
        for child in node.getChildNodes():
            self.dispatch(child)

    def visitFunction(self, node):
        if not hasattr(node, 'name'): # lambdas
            node.name = '<lambda>'
        vis = CCVisitor(node)
        self.stats.functions.append(vis.stats)

    visitLambda = visitFunction

    def visitClass(self, node):
        vis = CCVisitor(node)
        self.stats.classes.append(vis.stats)

    def visitIf(self, node):
        self.stats.complexity += len(node.tests)
        self.dispatchChildren(node)

    def __processDecisionPoint(self, node):
        self.stats.complexity += 1
        self.dispatchChildren(node)

    visitFor = __processDecisionPoint
    visitGenExprFor = __processDecisionPoint
    visitGenExprIf = __processDecisionPoint
    visitListCompFor = __processDecisionPoint
    visitListCompIf = __processDecisionPoint
    visitWhile = __processDecisionPoint
    visitWith = __processDecisionPoint
    visitAnd = __processDecisionPoint
    visitOr = __processDecisionPoint


def measure_file_complexity(filename):
    """Returns a FlatStats object for the contents of the file at filename."""
    modulename = utils.splitpath_root_file_ext(filename)[1]
    ast = compiler.parseFile(filename)
    ast.name = modulename
    visitor = CCVisitor(ast)
    return FlatStats(visitor.stats)


def measure_cyclcompl(files):
    """Returns 2 items:
    A collection of (filename, FlatStat instance for file) tuples,
    and a collection of files that failed to parse.
    """
    result = []
    failures = []
    for f in files:
        try:
            stats = measure_file_complexity(f)
            result.append((f, stats))
        except SyntaxError:
            failures.append(f)
    return result, failures