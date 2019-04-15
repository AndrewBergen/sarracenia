#!/usr/bin/env bash

#FIXME: puts the path at the end? so if you have multiple, guaranteed to take the wrong one?
#       psilva worry 2019/01
#
if [[ ":$SARRA_LIB/../:" != *":$PYTHONPATH:"* ]]; then
    if [ "${PYTHONPATH:${#PYTHONPATH}-1}" == ":" ]; then
        export PYTHONPATH="$PYTHONPATH$SARRA_LIB/../"
    else
        export PYTHONPATH="$PYTHONPATH:$SARRA_LIB/../"
    fi
fi

function application_dirs {
python3 << EOF
import appdirs

cachedir  = appdirs.user_cache_dir('sarra','science.gc.ca')
cachedir  = cachedir.replace(' ','\ ')
print('export CACHEDIR=%s'% cachedir)

confdir = appdirs.user_config_dir('sarra','science.gc.ca')
confdir = confdir.replace(' ','\ ')
print('export CONFDIR=%s'% confdir)

logdir  = appdirs.user_log_dir('sarra','science.gc.ca')
logdir  = logdir.replace(' ','\ ')
print('export LOGDIR=%s'% logdir)

EOF
}

function sr_action {
msg=$1
action=$2
files=$3

echo $msg $action $files
if [ "$SARRAC_LIB" ]; then
  echo $files | sed 's/ / ; sr_/g' | sed 's/$/ ;/' | sed 's/^/ sr_/' | sed "s+/+ $action +g" | grep -Po "sr_c[\w]* $action [\w\_\. ]* ;" | sed 's~^~"$SARRAC_LIB"/~' | sh
else
  echo $files | sed 's/ / ; sr_/g' | sed 's/$/ ;/' | sed 's/^/ sr_/' | sed "s+/+ $action +g" | grep -Po "sr_c[\w]* $action [\w\_\. ]* ;" | sh
fi

if [ "$SARRA_LIB" ]; then
  echo $files | sed 's/ / ; sr_/g' | sed 's/$/ ;/' | sed 's/^/ sr_/' | sed "s+/+ $action +g" | grep -Po "sr_[^c][\w]* $action [\w\_\. ]* ;" | sed 's/ /.py /' | sed 's~^~"$SARRA_LIB"/~' | sh
else
  echo $files | sed 's/ / ; sr_/g' | sed 's/$/ ;/' | sed 's/^/ sr_/' | sed "s+/+ $action +g" | grep -Po "sr_[^c][\w]* $action [\w\_\. ]* ;" | sh
fi
}

function qchk {
#
# qchk verify correct number of queues present.
#
# 1 - number of queues to expect.
# 2 - Description string.
# 3 - query
#
adminpw="`awk ' /bunnymaster:.*\@localhost/ { sub(/^.*:/,""); sub(/\@.*$/,""); print $1; exit }; ' "$CONFDIR"/credentials.conf`"
queue_cnt="`rabbitmqadmin -H localhost -u bunnymaster -p ${adminpw} -f tsv list queues | awk ' BEGIN {t=0;} (NR > 1)  && /_f[0-9][0-9]/ { t+=1; }; END { print t; };'`"

if [ "$queue_cnt" = $1 ]; then
    echo "OK, as expected $1 $2"
    passed_checks=$((${passed_checks}+1))
else
    echo "FAILED, expected $1, but there are $queue_cnt $2"
fi

count_of_checks=$((${count_of_checks}+1))

}

function xchk {
#
# qchk verify correct number of exchanges present.
#
# 1 - number of exchanges to expect.
# 2 - Description string.
#
adminpw="`awk ' /bunnymaster:.*\@localhost/ { sub(/^.*:/,""); sub(/\@.*$/,""); print $1; exit }; ' "$CONFDIR"/credentials.conf`"
exnow=${LOGDIR}/flow_setup.exchanges.txt
exex=flow_lists/exchanges_expected.txt
rabbitmqadmin -H localhost -u bunnymaster -p ${adminpw} -f tsv list exchanges | grep -v '^name' | grep -v amq\. | grep -v direct| sort >$exnow

x_cnt="`wc -l <$exnow`"
expected_cnt="`wc -l <$exex`"

if [ "$x_cnt" -ge $expected_cnt ]; then
    echo "OK, as expected $expected_cnt $1"
    passed_checks=$((${passed_checks}+1))
else
    echo "FAILED, expected $expected_cnt, but there are $x_cnt $1"
    printf "Missing exchanges: %s\n" "`comm -23 $exex $exnow`"
fi
if [ "$x_cnt" -gt $expected_cnt ]; then
    printf "NOTE: Extra exchanges: %s\n" "`comm -13 $exex $exnow`"
fi

count_of_checks=$((${count_of_checks}+1))

}





