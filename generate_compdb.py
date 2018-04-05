from __future__ import print_function

import argparse
import json
import os
import re
import shlex
import sys

RULE_PATTERN = re.compile(r'^\s*rule\s+(\S+)$')
COMMAND_PATTERN = re.compile(r'^\s*command\s*=\s*(.+)$')
BUILD_PATTERN = re.compile(r'^\s*build\s+.*:\s*(?P<rule>\S+)\s+(?P<file>\S+)')
CAT_PATTERN = re.compile(r'\\\$\$\(\s*cat\s+(\S+)\s*\)')
SUBCOMMAND_PATTERN = re.compile(r'\([^\)]*\)')
CCACHE_PATTERN = re.compile(r'^\s*\S*/ccache\s+(.*)$')
CLANG_PATTERN = re.compile(r'^\s*\S*/(?:clang|clang\+\+)\s+(.*)$')

def cat_expand(match):
    try:
        with open(match.group(1)) as cat_file:
            return cat_file.read().replace('\n', ' ').strip()
    except IOError as ex:
        print(ex, file=sys.stderr)


parser = argparse.ArgumentParser(description='Generate compile_commands.json for AOSP')
parser.add_argument('ninja_file')
args = parser.parse_args()

rules = {}
compdb = []
directory = os.path.abspath(os.getcwd())

with open(args.ninja_file) as ninja_file:
    for line in ninja_file:
        rule_match = RULE_PATTERN.match(line)
        if rule_match:
            rule_name = rule_match.group(1)
            continue

        command_match = COMMAND_PATTERN.match(line)
        if command_match:
            rules[rule_name] = command_match.group(1)
            continue

        build_match = BUILD_PATTERN.match(line)
        if build_match:
            command = rules.get(build_match.group('rule'))
            if command:
                command = CAT_PATTERN.sub(cat_expand, command)
                subcommands = SUBCOMMAND_PATTERN.findall(command)
                if subcommands:
                    command = subcommands[0][1:-1]

                ccache_match = CCACHE_PATTERN.match(command)
                if ccache_match:
                    command = ccache_match.group(1)

                if not CLANG_PATTERN.match(command):
                    continue

                compdb.append({
                    'directory': directory,
                    'command': command,
                    'file': build_match.group('file')
                })

with open('out/compile_commands.json', 'w') as compdb_file:
    json.dump(compdb, compdb_file, indent=1)
