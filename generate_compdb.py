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
CAT_PATTERN = re.compile(r'\\\$\$\(\s*cat\s+([^\)]+)\)')
SUBCOMMAND_PATTERN = re.compile(r'\(([^\)]*)\)')

rules = {}
compdb = []
directory = os.path.abspath(os.getcwd())
cat_cache = {}


def cat_expand(match):
    file_name = match.group(1).strip()

    if file_name in cat_cache:
        return cat_cache[file_name]

    try:
        with open(file_name) as cat_file:
            content = cat_file.read().replace('\n', ' ').strip()
    except IOError as ex:
        print(ex, file=sys.stderr)
        content = None

    cat_cache[file_name] = content
    return content


def parse_command(command, file):
    while command:
        first_space = command.find(' ', 1)
        if (first_space == -1):
            first_space = len(command)

        if command[0:first_space].endswith('/clang') or command[0:first_space].endswith('/clang++'):
            break

        command = command[first_space:]

    command = command.strip()

    if not command:
        return False

    compdb.append({
        'directory': directory,
        'command': command,
        'file': file
    })
    return True


parser = argparse.ArgumentParser(description='Generate compile_commands.json for AOSP')
target_product = os.getenv('TARGET_PRODUCT')
if target_product:
    parser.add_argument('ninja_file', nargs='?', default='out/build-{}.ninja'.format(target_product))
else:
    parser.add_argument('ninja_file')
args = parser.parse_args()

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
                file = build_match.group('file')
                command = CAT_PATTERN.sub(cat_expand, command)
                has_subcommands = False
                for subcommand in SUBCOMMAND_PATTERN.finditer(command):
                    has_subcommands = True
                    if parse_command(subcommand.group(1), file):
                        break
                if not has_subcommands:
                    parse_command(command, file)

with open('out/compile_commands.json', 'w') as compdb_file:
    json.dump(compdb, compdb_file, indent=1)
