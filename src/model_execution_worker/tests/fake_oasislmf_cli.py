"""Stand-in for `oasislmf model <command> --config <json>` used by test_oasis_cli.py.

Behaviour is chosen by the `mode` key of the config JSON.
"""
import json
import multiprocessing
import os
import subprocess
import sys
import time


def busy(pid_file):
    # like a model run: bash pipeline with a background child, a forked worker, CPU-bound python
    bash = subprocess.Popen(['bash', '-c', 'sleep 300 & echo $!; wait'], stdout=subprocess.PIPE)
    grandchild = int(bash.stdout.readline())
    forked = multiprocessing.get_context('fork').Process(target=time.sleep, args=(300,))
    forked.start()
    with open(pid_file + '.tmp', 'w') as f:
        json.dump({'cli': os.getpid(), 'bash': bash.pid, 'bash_child': grandchild, 'forked': forked.pid}, f)
    os.rename(pid_file + '.tmp', pid_file)
    while True:
        pass


def main(command, config_fp):
    with open(config_fp) as f:
        config = json.load(f)
    mode = config.get('mode')
    print(f'command={command}', flush=True)
    print(f'config={json.dumps(config, sort_keys=True)}', flush=True)
    if mode == 'ok':
        print('COMPLETED: run', file=sys.stderr, flush=True)
    elif mode == 'fail':
        print('Something went wrong', file=sys.stderr, flush=True)
        sys.exit(3)
    elif mode == 'no_keys':
        print('No successful lookup results found in the keys file - Check the `keys-errors.csv` file', flush=True)
        sys.exit(1)
    elif mode == 'busy':
        busy(config['pid_file'])
    elif mode == 'leave_background':
        subprocess.Popen(['bash', '-c', f'echo $$ > {config["pid_file"]}; exec sleep 300'], start_new_session=False)
        time.sleep(0.5)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
