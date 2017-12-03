#!/usr/bin/env python3
import math
import os
from collections import defaultdict
from functools import reduce

import junitparser
import jinja2


is_sucess = lambda result: result is None
is_skipped = lambda result: isinstance(result, junitparser.Skipped)
is_failure = lambda result: isinstance(result, junitparser.Failure)
is_error = lambda result: isinstance(result, junitparser.Error)


class Collector:
    def __init__(self):
        self.cases = []

    def add(self, case):
        self.cases.append(case)

    def __iter__(self):
        return iter(self.cases)

    @property
    def tests(self): return len(self.cases)

    @property
    def time(self):
        return reduce(lambda total, case: total + case.time, self.cases, 0.0)

    @property
    def skipped(self):
        return reduce(lambda total, case: total + is_skipped(case.result), self.cases, 0)

    @property
    def failures(self):
        return reduce(lambda total, case: total + is_failure(case.result), self.cases, 0)

    @property
    def errors(self):
        return reduce(lambda total, case: total + is_error(case.result), self.cases, 0)

    @property
    def successes(self):
        return reduce(lambda total, case: total + is_sucess(case.result), self.cases, 0)

    @property
    def non_skipped(self):
        return max(self.tests - self.skipped, 0)


def percent_filter(value, total, decimal_places=2):
    precision = math.pow(10, decimal_places)
    return math.floor(precision * value * 100.0 / total) / precision


def result_filter(result):
    if is_sucess(result): return "Success"
    if is_skipped(result): return "Skipped"
    if is_failure(result): return "Failure"
    if is_error(result): return "Error"
    return "???"


def template_with_loader(path):
    """
    Given a file system `path`, create a jinja FileSystemLoader for that
    path and return a ``(loader, template basename)`` tuple. This allows
    to specify template as an fs path, but allow template subclassing and
    all that jazz from the directory of the template provided.
    """
    path, filename = os.path.split(path)
    loader = jinja2.FileSystemLoader(path, followlinks=True)

    return loader, filename


def report_generator(xml_files, template_file):

    totals = Collector()
    per_class = defaultdict(Collector)

    def update_class_statistics(test_case):
        totals.add(test_case)
        per_class[test_case.classname].add(test_case)

    for filename in xml_files:
        xml = junitparser.JUnitXml.fromfile(filename)

        for suite in xml:
            if isinstance(suite, junitparser.TestCase):
                update_class_statistics(suite)
            elif isinstance(suite, junitparser.TestSuite):
                for test in suite: update_class_statistics(test)

    template_loader, template_name = template_with_loader(template_file)

    env = jinja2.Environment(loader=template_loader)
    env.filters['percent'] = percent_filter
    env.filters['result'] = result_filter
    tmpl = env.get_template(template_name)
    print(tmpl.render(totals=totals, per_class=per_class))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("usage: %s <jinja2 template> <junit xml> [<junit xml> ...]" % sys.argv[0], file=sys.stderr)
        exit(1)

    report_generator(sys.argv[2:], sys.argv[1])
