#!/bin/bash
script_path=`dirname "$BASH_SOURCE"`
if [ ! "$1" ]; then
	echo Usage: $0 IMAGEJ_PLUGIN_DIR
	exit 1
fi
imagej_plugins=$1

cd $script_path
set -x -e
rm -rf "$imagej_plugins/plugins/FISH_Join" "$imagej_plugins/jars/Lib/fish_join_modules"
cp -R FISH_Join "${imagej_plugins}/plugins/FISH_Join"
cp -R fish_join_modules "$imagej_plugins/jars/Lib/fish_join_modules"
