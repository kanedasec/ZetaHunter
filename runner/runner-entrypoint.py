#!/usr/bin/env python3
import sys
import subprocess
import os

if __name__ == '__main__':
    # basic entrypoint to keep container running and accept manual testing
    print('runner container up')
    # we could implement a simple watcher or HTTP API here
    while True:
        import time
        time.sleep(60)
