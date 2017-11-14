#!/usr/bin/env python
import argparse
import errno    
import os
import stat
import json

LOCAL_DIR = '~/.gate'
LOCAL_CONF = 'config.json'

def mkdir_p(path):
    """
    Creates a directory if it doesn't already exist. In other words, `mkdir -p` equivalent in python.
    https://stackoverflow.com/a/600612
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def get_local_dir():
    # Better to expand the path at runtime rather than at import time.
    return os.path.expanduser(LOCAL_DIR)

def get_config_path():
    return os.path.join(get_local_dir(), LOCAL_CONF)

def mysql_src(variables):

    variables['backend'] = 'mycli'

    src = """\
#!/bin/bash

export GLOBIGNORE="*"

FLAGS=''
FLAGS+=' --host={host}'
FLAGS+=' --port={port}'
FLAGS+=' --user={user}'
# FLAGS+=' -t' # table format
FLAGS+=" --password={password}"

if [ -n "$1" ]; then
	FLAGS+=" --execute=\"$1\""
fi

COMMAND="{backend} $FLAGS giphy"

eval $COMMAND""".format(**variables)

    return src


def init():

    # make sure the local directory exists
    local_dir_path = get_local_dir()
    mkdir_p(local_dir_path)

    config_file_path = get_config_path()

    # create a config file if there isn't one
    if not os.path.isfile(config_file_path):
        with open(config_file_path, 'w') as fd:
            fd.write('{}')

    # config file contains passwords, so only the owner should be able to read/write
    os.chmod(local_dir_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    os.chmod(config_file_path, stat.S_IRUSR | stat.S_IWUSR)

    with open(config_file_path, 'r') as fd:
        return json.load(fd)

def parse_args():
    """ Parses arguments. """
    parser = argparse.ArgumentParser(
        description='Easily manage remote access CLI scripts.')
    parser.add_argument('-v', '--verbose',
        action='store_true',
        help='verbose output')
    return parser.parse_args()

def write_files(config, args):

    def missing_property(name, key):
        raise Exception(
                '{name} missing "{key}" property! Check your config file at "{path}".'
                .format(name=name, key=key, path=get_config_path()))

    def get(name, obj, key):
        value = obj.get(key, None)
        if value is None:
            missing_property(name, key)
        return value

    type_src_table = {
        "mysql": mysql_src
    }

    if not config.get('namespaces', {}):
        print("[!] no namespaces found")

    for name, namespace in config.get('namespaces', {}).items():

        print('[*] writing files for: {name}'.format(name=name))

        namespace_path = os.path.expanduser(get('namespace', namespace, 'path'))
        entries = get('namespace', namespace, 'entries')

        mkdir_p(namespace_path)
        os.chmod(namespace_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

        for entry in entries:
            
            entry_type, entry_alias = (
                get('entry', entry, 'type'),
                get('entry', entry, 'alias')
            )

            src_func = type_src_table.get(entry_type, None)
            if not src_func:
                raise Exception('Unsupported type: {entry_type}.'.format(entry_type=entry_type))

            src = src_func(entry)

            filename = "{entry_type}.{entry_alias}.sh".format(entry_type=entry_type, entry_alias=entry_alias)

            entry_path = os.path.join(namespace_path, filename)

            with open(entry_path, 'w') as fd:
                fd.write(src)

            print('[*] wrote file: {entry_path}'.format(entry_path=entry_path))

            # read write execute for the owner only
            os.chmod(entry_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

def main():
    
    config = init()
    print("[*] loaded config: %s" % get_local_dir())

    args = parse_args()
    
    write_files(config, args)

    config_file_path = get_config_path()
    with open(config_file_path, 'w') as fd:
        json.dump(config, fd, indent=2)

if __name__ == '__main__':
    main()
