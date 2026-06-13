import argparse
from runtime import run_container

def main():
	parser = argparse.ArgumentParser(prog="mdocker")
	subparser = parser.add_subparsers(dest="subcommand", required=True)

	run_parser = subparser.add_parser("run", help="Run a command in a new container")
	run_parser.add_argument("command", nargs="+")

	args = parser.parse_args()
	if args.subcommand == "run":
		run_container(args.command)

if __name__ == "__main__":
	main()
