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
    from sr_config import sr_config
    from sr_instances import sr_instances
    from sr_poll import sr_poll
    from sr_post import sr_post
    from sr_report import sr_report
    from sr_sarra import sr_sarra
    from sr_sender import sr_sender
    from sr_shovel import sr_shovel
    from sr_subscribe import sr_subscribe
    from sr_watch import sr_watch
    from sr_winnow import sr_winnow
except:
    from sarra.sr_config import sr_config
    from sarra.sr_instances import sr_instances
    from sarra.sr_poll import sr_poll
    from sarra.sr_post import sr_post
    from sarra.sr_report import sr_report
    from sarra.sr_sarra import sr_sarra
    from sarra.sr_sender import sr_sender
    from sarra.sr_shovel import sr_shovel
    from sarra.sr_subscribe import sr_subscribe
    from sarra.sr_watch import sr_watch
    from sarra.sr_winnow import sr_winnow


def instantiate(cfg, pgm, confname, action):
    """ Instantiate and execute action on program using its configuration file

    Executing cleanup, declare, setup and remove actions on python program, but audit and c stuff
    is a different case and require to spawn a call

    :param cfg: the instance providing the logger and the execution context
    :param pgm: the name of the process to run
    :param confname: the name of the configuration to use
    :param action: the action to apply on the process
    :return: None
    """
    if pgm not in ['audit', 'cpost', 'cpump']:
        config = re.sub(r'(\.conf)', '', confname)
        orig = sys.argv[0]
        # FIXME this seems a wrong thing to do (changing prog name so that underlying instances reparse args)
        sys.argv[0] = 'sr_' + pgm
        try:
            cfg.logger.debug("sr_%s %s %s" % (pgm, action, config))
            if pgm == 'poll':
                inst = sr_poll(config, [action])
            elif pgm == 'post':
                inst = sr_post(config, [action])
            elif pgm == 'sarra':
                inst = sr_sarra(config, [action])
            elif pgm == 'sender':
                inst = sr_sender(config, [action])
            elif pgm == 'shovel':
                inst = sr_shovel(config, [action])
            elif pgm == 'subscribe':
                inst = sr_subscribe(config, [action])
            elif pgm == 'watch':
                inst = sr_watch(config, [action])
            elif pgm == 'winnow':
                inst = sr_winnow(config, [action])
            else:
                inst = sr_report(config, [action])
            inst.logger = cfg.logger
            inst.exec_action(action, False)
        except:
            cfg.logger.error("could not instantiate and run sr_%s %s %s" % (pgm, action, confname))
            cfg.logger.debug('Exception details: ', exc_info=True)
            sys.exit(1)
        sys.argv[0] = orig
    else:
        # try to avoid error code while running sanity
        cfg.logger.debug("sr_%s %s %s" % (pgm, action, confname))
        cfg.run_command(["sr_" + pgm, action, confname])


def invoke(cfg, pgm, confname, action):
    """ Invoke a program as a process with its action and using its configuration file.

    sr_post is run as a special case needed

    :param cfg: the instance providing the logger and the execution context
    :param pgm: the name of the process to run
    :param confname: the name of the configuration to use
    :param action: the action to apply on the process
    :return: None
    """
    program = 'sr_' + pgm
    config = re.sub(r'(\.conf)', '', confname)

    try:
        if program != 'sr_post':
            # anything but sr_post
            cfg.logger.debug("%s %s %s" % (program, action, config))
            cfg.run_command([program, action, config])
        else:
            confpath = cfg.user_config_dir + os.sep + pgm + os.sep + confname
            sleeps = False
            if action == 'status':
                f = open(confpath, 'r')
                for line in f.readlines():
                    tokens = line.split()
                    if len(tokens) >= 2 and tokens[0] == 'sleep' and float(tokens[1]) > 0:
                        sleeps = True
                f.close()
            if not sleeps:
                # sr_post needs -c with absolute confpath
                cfg.logger.debug("%s %s %s %s" % (program, '-c', confpath, action))
                cfg.run_command([program, '-c', confpath, action])
    except:
        cfg.logger.error("Invoke failed")
        cfg.logger.debug('Exception details: ', exc_info=True)


def scandir(cfg, pgm, action):
    """ Recursive scan of ~/.config/sarra/*.

    Always run sr_audit when provided (doesn't needs a config), instanciating a process on selected actions
    (cleanup, declare and setup) and invoking the process in other cases. Process are named from the parent directory
    (except for sr_audit).

    :param cfg: the instance providing the logger and the execution context
    :param pgm: the name of the process to run
    :param action: the action to apply on the process
    :return: None
    """
    config_path = cfg.user_config_dir + os.sep + pgm

    if os.path.isdir(config_path) and os.listdir(config_path):
        cfg.logger.info("{} {}".format(config_path, action))
        # The config path exist
        for confname in os.listdir(config_path):
            is_config = len(confname) >= 5 and '.conf' in confname[-5:]
            is_include = len(confname) >= 4 and '.inc' in confname[-4:]
            if is_config and action in ['cleanup', 'declare', 'setup']:
                instantiate(cfg, pgm, confname, action)
            elif is_config or is_include and action == 'remove':
                invoke(cfg, pgm, confname, action)
    elif pgm == 'audit':
        # The config path doesn't exist but we launch sr_audit
        cfg.logger.info("sr_%s %s" % (pgm, action))
        cfg.run_command(['sr_' + pgm, action])


# ===================================
# MAIN
# ===================================

def main():
    """ Start multiple Sarracenia configurations from this main entry point.

    This function parses arguments accepted by this module, create a first logger as sr_instance
    and then execute its main loop.

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
        # List plugins
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
        for pgm in sorted(cfg.programs):
            cfg.print_configdir("configuration examples", cfg.package_dir + os.sep + 'examples' + os.sep + pgm)
        cfg.print_configdir("general", cfg.user_config_dir)
        for pgm in sorted(cfg.programs):
            cfg.print_configdir("user configurations", cfg.user_config_dir + os.sep + pgm)
    elif not args.config:
        # Executing other actions than list
        cfg.setlog()
        if args.action != 'remove' or cfg.sr_remove:
            for pgm in ['audit'] + cfg.programs:
                scandir(cfg, pgm, args.action)
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
