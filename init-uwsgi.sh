#!/usr/bin/env bash

########## Settings ##########
APP_NAME="lambdaoj"
INI_FILE=$APP_NAME.ini
SH_FILE="run.sh"

CURRENT_PATH=$(pwd)
CURRENT_USER=$USER
CURRENT_GROUP=$(groups | cut -d' ' -f1)
DEFAULT_PORT="9900"
DEFAULT_WORKERS="2"


########## INI_FILE ##########
read -p "OJ Web User ($CURRENT_USER) : " OJ_WEB_USER
read -p "OJ Web Group ($CURRENT_GROUP) : " OJ_WEB_GROUP
read -p "uWSGI Listem Port ($DEFAULT_PORT) : " OJ_PORT
read -p "uWSGI Workers ($DEFAULT_WORKERS) : " OJ_WORKERS

{
    printf "[uwsgi]\n"
    printf "pythonpath = %s\n" $CURRENT_PATH
    printf "pidfile = %s\n"    $CURRENT_PATH/tmp/uwsgi.pid
    printf "module = %s\n"     $APP_NAME
    printf "master = true\n"
    printf "workers = %s\n"    ${OJ_WORKERS:-$DEFAULT_WORKERS}
    printf "uid = %s\n"        ${OJ_WEB_USER:-$CURRENT_USER}
    printf "gid = %s\n"        ${OJ_WEB_GROUP:-$CURRENT_GROUP}
    printf "socket = :%s\n"    ${OJ_PORT:-$DEFAULT_PORT}
    printf "callable = app\n"
} > $INI_FILE



########## SH_FILE ###########
{
    echo "#!/usr/bin/env bash"
    echo
    echo "cd " $CURRENT_PATH
    echo "mkdir -p tmp"
    echo
    echo "judge/lambdajudge &"
    echo
    echo "source venv/bin/activate"
    echo "uwsgi --ini lambdaoj.ini -H "$CURRENT_PATH"/venv >/dev/null 2>&1 &"
} > $SH_FILE

chmod 0755 $SH_FILE



############ END #############
exit 0
