import argparse, sys
from .domestic_zapi.pipeline import run as run_domestic
from .export_orders.pipeline import run as run_export

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="parsingtool", description="Parsing Tool CLI")
    sub = p.add_subparsers(dest="command")  # not required=True

    p_dom = sub.add_parser("domestic", help="Parse Domestic ZAPI PDF -> Batches CSV and SSCC CSV")
    p_dom.add_argument("input_pdf")
    p_dom.add_argument("--out-batches", required=True)
    p_dom.add_argument("--out-sscc", required=True)

    p_exp = sub.add_parser("export", help="Parse Export PDF (placeholder)")
    p_exp.add_argument("input_pdf")
    p_exp.add_argument("--out", required=True)
    return p

def main() -> None:
    parser = build_parser()

    # If user ran just `parsingtool`, show help and exit 0
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # If user ran a single --help/-h, also exit 0
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "domestic":
        run_domestic(input_pdf=args.input_pdf, out_batches=args.out_batches, out_sscc=args.out_sscc)
        return

    if args.command == "export":
        run_export(input_pdf=args.input_pdf, out=args.out)
    return


    parser.print_help()
    sys.exit(0)

if __name__ == "__main__":
    main()
