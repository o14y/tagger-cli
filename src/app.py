import logging
import os
import sys
import readline
import shlex
from dataclasses import dataclass
from simple_parsing import field, ArgumentParser
from models.context import Context
from commands.cli import Cli
from pathlib import Path

@dataclass
class App:
    path :Path = field(positional=True, help='Path to the directory to read')
    def run(self):
        context = Context(path=self.path)
        while context.exiting == False:
            try:
                line = input('> ')
                readline.add_history(line)
                args = shlex.split(line)
                parser = ArgumentParser()
                parser.add_arguments(Cli, dest='cli')
                cli = parser.parse_args(args).cli
                cli.run(context)
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
            except SystemExit as e:
                pass
            except Exception as e:
                print(f"⚠ {e}", file=sys.stderr)

def main():
    print('ctrl+d to exit.')
    parser = ArgumentParser()
    parser.add_arguments(App, dest='app')
    app = parser.parse_args().app
    app.run()

if __name__ == '__main__':
    log_level = os.environ.get('TAGGER_LOG_LEVEL', 'WARN').upper() 
    logging.basicConfig(level=log_level)
    log = logging.getLogger(__name__)
    main()
