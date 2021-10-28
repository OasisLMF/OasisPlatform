#!/bin/bash

SD=$(dirname $0)

exec $SD/worker_controller.py
