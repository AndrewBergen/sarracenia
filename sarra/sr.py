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
import logging, os, os.path, shutil, sys, time

try:
    from sr_config import *
    from sr_poll import *
    from sr_post import *
    from sr_report import *
    from sr_sarra import *
    from sr_sender import *
    from sr_shovel import *
    from sr_subscribe import *
    from sr_watch import *
    from sr_winnow import *
except:
    from sarra.sr_config import *
    from sarra.sr_poll import *
    from sarra.sr_post import *
    from sarra.sr_report import *
    from sarra.sr_sarra import *
    from sarra.sr_sender import *
    from sarra.sr_shovel import *
    from sarra.sr_subscribe import *
    from sarra.sr_watch import *
    from sarra.sr_winnow import *


def instantiate(cfg, pgm, confname, action):
    """ Instantiate each program  with its configuration file

    And invoke action if one of cleanup,declare,setup

    :param cfg:
    :param pgm:
    :param confname:
    :param action:
    :return:
    """
    # c stuff always requiere to spawn a call

    if pgm in ['audit', 'cpost', 'cpump']:
        # try to avoid error code while running sanity
        if action == 'sanity': return
        cfg.logger.debug("%s %s %s" % ("sr_" + pgm, action, confname))
        cfg.run_command(["sr_" + pgm, action, confname])
        return

    config = re.sub(r'(\.conf)', '', confname)
    orig = sys.argv[0]

    sys.argv[0] = 'sr_' + pgm

    try:
        inst = None
        cfg.logger.debug("inst %s %s %s" % (pgm, config, action))
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
        elif pgm == 'report':
            inst = sr_report(config, [action])
        elif pgm == 'audit':
            inst = sr_audit(config, [action])
        else:
            cfg.logger.error("code not configured for process type sr_%s" % pgm)
            sys.exit(1)

        inst.logger = cfg.logger

        if action == 'cleanup':
            inst.exec_action('cleanup', False)
        elif action == 'declare':
            inst.exec_action('declare', False)
        elif action == 'setup':
            inst.exec_action('setup', False)

        elif action == 'remove':
            inst.exec_action('remove', False)

        sys.argv[0] = orig

    except:
        cfg.logger.error("could not instantiate and run sr_%s %s %s" % (pgm, action, confname))
        cfg.logger.debug('Exception details: ', exc_info=True)
        sys.exit(1)


def invoke(cfg, pgm, confname, action):
    """ Invoke each program with its action and configuration file

    :param cfg:
    :param pgm:
    :param confname:
    :param action:
    :return:
    """
    program = 'sr_' + pgm
    config = re.sub(r'(\.conf)', '', confname)

    # c does not implement action sanity yet
    cfg.logger.info("action %s" % action)

    try:
        # anything but sr_post
        if program != 'sr_post':
            cfg.logger.debug("%s %s %s" % (program, action, config))
            cfg.run_command([program, action, config])
        else:
            # sr_post needs -c with absolute confpath
            confpath = cfg.user_config_dir + os.sep + pgm + os.sep + confname
            sleeps = False
            if (action == 'status'):
                f = open(confpath, 'r')
                for li in f.readlines():
                    l = li.split()
                    if len(l) < 2:
                        continue

                    if l[0] == 'sleep':
                        if float(l[1]) > 0:
                            sleeps = True
                f.close()
            if not sleeps:
                return
            post = sr_post(confpath)
            cfg.logger.debug("INVOKE %s %s %s %s" % (program, '-c', confpath, action))
            cfg.run_command([program, '-c', confpath, action])
    except:
        cfg.logger.error("Invoke failed")
        cfg.logger.debug('Exception details: ', exc_info=True)


def scandir(cfg, pgm, action):
    """ Recursive scan of ~/.config/sarra/* , invoking process according to

    the process named from the parent directory

    :param cfg:
    :param pgm:
    :param action:
    :return:
    """
    config_path = cfg.user_config_dir + os.sep + pgm
    configpath_exist = os.path.isdir(config_path) and os.listdir(config_path)

    if not configpath_exist and pgm == 'audit':
        cfg.logger.info("sr_%s %s" % (pgm, action))
        cfg.run_command(['sr_' + pgm, action])
    elif configpath_exist:
        for confname in os.listdir(config_path):
            if len(confname) >= 5 and '.conf' in confname[-5:]:
                cfg.logger.info("%s %s %s" % (pgm, action, confname))
                if action in ['cleanup', 'declare', 'setup']:
                    instantiate(cfg, pgm, confname, action)
                else:
                    invoke(cfg, pgm, confname, action)
    else:
        cfg.logger.debug('No configuration found for sr_%s in %s' % (pgm, cfg.user_config_dir))


# ===================================
# MAIN
# ===================================

def main():
    # Parsing args
    actions_supported = ['start', 'stop', 'status', 'sanity', 'restart', 'reload', 'remove',
                         'cleanup', 'declare', 'setup']
    actions_supported.extend(['list'])
    parser = argparse.ArgumentParser(description='Sarracenia {}'.format(sarra.__version__))
    parser.add_argument('action', metavar='action', choices=actions_supported,
                        help='Action supported by sr: {}'.format(actions_supported))
    parser.add_argument('-d', '--debug', action='store_true', help='Running in debug mode')
    parser.add_argument('config', metavar='config', nargs='?',
                        help='Only if the action is list: an empty config will list all configurations available, '
                             '"plugin" keyword will list all plugins available and any other name will print '
                             'the config file content if the file exists')
    args = parser.parse_args()

    # Uses sr_instances to get a good logger
    if args.debug:
        cfg = sr_instances(args=sys.argv)
    else:
        cfg = sr_instances(args=sys.argv[:1])
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
    elif args.action and not args.config:
        # Execute action on all configured processes

        # Init logger here
        cfg.setlog()

        # loop on all possible programs add audit at beginning
        for pgm in ['audit'] + cfg.programs:
            scandir(cfg, pgm, args.action)
    else:
        cfg.logger.error('Wrong argument: {}'.format(args.config))


# =========================================
# direct invocation
# =========================================

if __name__ == "__main__":
    main()
