from . import cli

cli.parser.prog = __package__

if __name__ == '__main__':
    cli.main_with_conf()
