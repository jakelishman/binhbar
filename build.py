#!/usr/bin/env python

import argparse
import functools
import sys
from lib import hbar


class AppendOperation(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        namespace.operations = namespace.operations or []
        operation = functools.partial(self.const, *values)
        namespace.operations.append(operation)


_parser = argparse.ArgumentParser(
        epilog=("At least one operation must be specified."
                " Operations will be performed in order of specification."))
_parser.add_argument('--force', action='store_true')
_parser.add_argument('--update', nargs=1, const=hbar.update_article,
                     metavar='article_dir', dest='operations',
                     action=AppendOperation)
_parser.add_argument('--update-all', nargs=0, const=hbar.update_all_articles,
                     dest='operations', action=AppendOperation)
_parser.add_argument('--tidy-up', nargs=0, const=hbar.tidy_up,
                     dest='operations', action=AppendOperation)
_parser.add_argument('--deploy', nargs=0, const=hbar.deploy_site,
                     dest='operations', action=AppendOperation)


def main():
    args = _parser.parse_args()
    exit_code = 0
    if not args.operations:
        _parser.print_help()
        sys.exit(1)
    for operation in args.operations:
        exit_code += operation(vars=vars(args))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
