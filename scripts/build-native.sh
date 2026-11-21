#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p .build
if [ "${1:-host}" = device ]; then
 "${ZIG:-zig}" cc -target x86_64-linux-gnu.2.35 -std=c11 -Wall -Wextra -Werror -O2 -shared -fPIC src/native.c -o .build/engine-device.so -lm -lpthread -ldl
else
 cc -std=c11 -Wall -Wextra -Werror -O2 -shared -fPIC src/native.c -o .build/engine.so -lm -lpthread -ldl
fi
