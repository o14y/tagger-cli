#!/usr/bin/env bash
pushd $(dirname $0) > /dev/null
. venv/bin/activate
python src/app.py $*
deactivate
popd > /dev/null
