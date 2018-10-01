from . import cli

cli.parser.prog = __package__
cli.main_with_conf()
