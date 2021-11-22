#!/usr/bin/env bash

docker run -it --rm \
--add-host spine1:100.123.13.211 \
--add-host spine2:100.123.13.212 \
--add-host leaf1:100.123.13.213 \
--add-host leaf2:100.123.13.214 \
-v $PWD/counters:/scripts/counters \
pyez-triage:1.0 "$@"
