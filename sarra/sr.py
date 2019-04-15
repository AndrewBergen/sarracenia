#!/usr/bin/env python3
#
# This file is part of sarracenia.
# The sarracenia suite is Free and is proudly provided by the Government of Canada
# Copyright (C) Her Majesty The Queen in Right of Canada, Environment Canada, 2008-2015
#
# Questions or bugs report: dps-client@ec.gc.ca
# Sarracenia repository: https://github.com/MetPX/sarracenia
# Documentation: https://github.com/MetPX/sarracenia
#
# sr.py : python3 program starting an environment of sarra processes
#         found under ~/.config/sarra/*
#
#
# Code contributed by:
#  Michel Grenier - Shared Services Canada
#  Last Changed   : Sep 22 10:41:32 EDT 2015
#  Last Revision  : Sep 22 10:41:32 EDT 2015
#
########################################################################
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; version 2 of the License.
#
#  This program is distributed in the hope that it will be useful, 
#  but WITHOUT ANY WARRANTY; without even the implied warranty of 
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
#
#
import argparse
import os, os.path, sys, re
import sarra

try:
    from sr_audit import sr_audit
    from sr_post import sr_post
    from sr_watch import sr_watch
    from sr_winnow import sr_winnow
    from sr_sarra import sr_sarra
    from sr_shovel import sr_shovel
    from sr_subscribe import sr_subscribe
    from sr_sender import sr_sender
    from sr_poll import sr_poll
    from sr_report import sr_report
    from sr_instances import sr_instances
except:
    from sarra.sr_audit import sr_audit
    from sarra.sr_post import sr_post
    from sarra.sr_watch import sr_watch
    from sarra.sr_winnow import sr_winnow
    from sarra.sr_sarra import sr_sarra
    from sarra.sr_shovel import sr_shovel
    from sarra.sr_subscribe import sr_subscribe
    from sarra.sr_sender import sr_sender
    from sarra.sr_poll import sr_poll
    from sarra.sr_report import sr_report
    from sarra.sr_instances import sr_instances


def run_from_instance(cfg, pgm, action, config_name):
    """ Instantiate and execute action on program using its configuration file

    It is using reflection to instantiate a class known by this module as the program name is provided as argument(pgm).

    :param cfg: the instance providing the logger and the execution context
    :param pgm: the name of the process to run
    :param action: the action to apply on the process
    :param config_name: the name of the configuration to use
    :return: None
    """
    config = re.sub(r'(\.conf)', '', config_name)
    orig = sys.argv[0]
    sys.argv[0] = pgm
    cfg.logger.debug("{} {} {} {}".format(pgm, sys.argv[0], action, config))
    try:
        inst = getattr(sys.modules[__name__], pgm)(config, [action])
        inst.logger = cfg.logger
        inst.exec_action(action, False)
    except:
        cfg.logger.error("could not instantiate and run sr_%s %s %s" % (pgm, action, config_name))
        cfg.logger.debug('Exception details: ', exc_info=True)
        sys.exit(1)
    sys.argv[0] = orig


def run_from_cmd(cfg, pgm_name, action, config_name=''):
    """ Invoke a program as a process with its action and using its configuration file.

    sr_post is run as a special case needed only on a status action when it is set to sleep, this is because sr_post is
    not a daemon contrarily to other process.

    :param cfg: the instance providing the logger and the execution context
    :param pgm_name: the name of the process to run
    :param action: the action to apply on the process
    :param config_name: the name of the configuration to use
    :return: None
    """

    if pgm_name != 'sr_post':
        config = [re.sub(r'(\.conf)', '', config_name)] if config_name else []
        cfg.logger.debug("%s %s %s" % (pgm_name, action, config))
        cfg.run_command([pgm_name, action] + config)
    else:
        confpath = os.path.join(cfg.user_config_dir, pgm_name, config_name)
        sleeps = False
        if action == 'status':
            try:
                f = open(confpath, 'r')
                for line in f.readlines():
                    tokens = line.split()
                    if len(tokens) >= 2 and tokens[0] == 'sleep' and float(tokens[1]) > 0:
                        sleeps = True
                f.close()
            except OSError as err:
                cfg.logger.error("Cannot open file: {}".format(confpath))
                cfg.logger.debug('Exception details: ', exc_info=True)
        if sleeps:
            # sr_post needs -c with absolute confpath
            cfg.logger.debug("%s %s %s %s" % (pgm_name, '-c', confpath, action))
            cfg.run_command([pgm_name, '-c', confpath, action])


def scandir(cfg, pgm_name, action):
    """ Recursive scan of ~/.config/sarra/*.

    Always run sr_audit when provided (doesn't needs a config), run from instance on those selected actions (cleanup,
    declare and setup) when not using these programs (sr_cpost, sr_cpump). In other cases, it is running as a command.
    Process are named from the named config directory (except for sr_audit).

    :param cfg: the instance providing the logger and the execution context
    :param pgm_name: the name of the process to run
    :param action: the action to apply on the process
    :return: None
    """
    config_path = os.path.join(cfg.user_config_dir, pgm_name.replace('sr_', ''))

    if os.path.isdir(config_path) and os.listdir(config_path):
        # The config path exist
        cfg.logger.info("{} {}".format(config_path, action))
        for config_name in os.listdir(config_path):
            is_config = validate_extension(config_name, '.conf')
            is_include = validate_extension(config_name, '.inc')
            if is_config and action in ['cleanup', 'declare', 'setup'] and pgm_name not in ['sr_cpost', 'sr_cpump']:
                run_from_instance(cfg, pgm_name, action, config_name)
            elif is_config or is_include and action == 'remove':
                run_from_cmd(cfg, pgm_name, action, config_name)
    elif pgm_name == 'sr_audit':
        # The config path doesn't exist but we launch sr_audit
        cfg.logger.info("%s %s" % (pgm_name, action))
        run_from_cmd(cfg, pgm_name, action)


def validate_extension(config_name, ext):
    return len(config_name) > len(ext) and ext in config_name[-(len(ext) + 1):]


# ===================================
# MAIN
# ===================================

def main():
    """ Start multiple Sarracenia configurations from this main entry point.

    This function parses arguments accepted by this module, create a first logger as sr_instance and then execute its
    main switch.

    :return: None
    """
    # Parsing args
    actions_supported = ['start', 'stop', 'status', 'sanity', 'restart', 'reload']
    actions_supported.extend(['remove', 'cleanup', 'declare', 'setup'])
    actions_supported.extend(['list'])
    parser = argparse.ArgumentParser(description='Sarracenia {}'.format(sarra.__version__))
    parser.add_argument('action', metavar='action', choices=actions_supported,
                        help='Action supported by sr: {}'.format(actions_supported))
    parser.add_argument('-d', '--debug', action='store_const', const=['-debug'], default=[],
                        help='Running in debug mode')
    parser.add_argument('config', metavar='config', nargs='?',
                        help='Config is only supported with a "list" action. '
                             '"list": list all configurations available, '
                             '"list plugins": list all plugins available, '
                             '"list <my_config.conf>": print content of <my_config.conf> file if the file exists')
    args = parser.parse_args()

    # Uses sr_instances to get a good logger
    cfg = sr_instances(args=sys.argv[:1] + args.debug)
    cfg.build_instance(1)

    # Main switch
    if args.action == 'list' and args.config and args.config == 'plugins':
        # List all plugins
        cfg.print_configdir("packaged plugins", cfg.package_dir + os.sep + 'plugins')
        cfg.print_configdir("user plugins", cfg.user_config_dir + os.sep + 'plugins')
    elif args.action == 'list' and args.config:
        # Print config file content
        result = cfg.find_conf_file(args.config)
        if not result:
            cfg.logger.error("no file named %s found in all sarra configs" % args.config)
            sys.exit(1)
        cfg.list_file(result)
    elif args.action == 'list':
        # List all configs
        for pgm_name in sorted(cfg.programs):
            cfg.print_configdir("configuration examples", cfg.package_dir + os.sep + 'examples' + os.sep + pgm_name)
        cfg.print_configdir("general", cfg.user_config_dir)
        for pgm_name in sorted(cfg.programs):
            cfg.print_configdir("user configurations", cfg.user_config_dir + os.sep + pgm_name)
    elif not args.config:
        # Executing other actions than list
        cfg.setlog()
        programs = [pgm for pgm in globals().copy() if pgm.startswith('sr_') and pgm != 'sr_instances']

        if args.action != 'remove' or cfg.sr_remove:
            for pgm_name in programs + ['sr_cpost', 'sr_cpump']:
                scandir(cfg, pgm_name, args.action)
        else:
            cfg.logger.info("Command: 'sr {}' is not allowed".format(args.action))
    else:
        # A wrong argument unhandled by argparse (yet)
        cfg.logger.error('Action ({}) does not support a config argument'.format(args.action))
        parser.print_help()
        sys.exit(1)


# =========================================
# direct invocation
# =========================================

if __name__ == "__main__":
    main()
