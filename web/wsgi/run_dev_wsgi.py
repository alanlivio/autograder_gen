# This file used only by make dev_deploy

import sys
import importlib.util
from importlib.machinery import SourceFileLoader
from gunicorn.app.wsgiapp import run

wsgi_path = '/var/www/autograder/autograder.wsgi'
module_name = 'autograder.wsgi'

loader = SourceFileLoader(module_name, wsgi_path)
spec = importlib.util.spec_from_loader(module_name, loader)
mod = importlib.util.module_from_spec(spec)
sys.modules[module_name] = mod
loader.exec_module(mod)

if __name__ == '__main__':
    sys.argv = [sys.argv[0], '--bind', '127.0.0.1:8000', 'autograder.wsgi:application']
    run()
