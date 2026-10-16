import argparse
from pathlib import Path

from app.db.session import get_session_factory, init_db
import json

from app.services.importer import import_csv_text, import_json_text, import_synthetic
from app.services.inventory import initialize_official_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Utilidades locales de Campuslands Ops")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    sub.add_parser("import-synthetic")
    sub.add_parser("init-official")
    file_parser = sub.add_parser("import-file")
    file_parser.add_argument("path")
    file_parser.add_argument("--entity", default=None)
    args = parser.parse_args()

    init_db()
    if args.command == "init-db":
        print("Esquema listo. No se cargaron datos.")
        return

    session = get_session_factory()()
    try:
        if args.command == "import-synthetic":
            report = import_synthetic(session)
        elif args.command == "init-official":
            print(json.dumps(initialize_official_catalog(session), indent=2, default=str))
            return
        else:
            path = Path(args.path)
            text = path.read_text(encoding="utf-8-sig")
            if path.suffix.lower() == ".csv":
                if not args.entity:
                    raise SystemExit("Un CSV requiere --entity spaces|resources|reservations|loans|incidents")
                report = import_csv_text(session, text, args.entity, path.name)
            else:
                report = import_json_text(session, text, path.name)
        print(report.model_dump_json(indent=2))
    finally:
        session.close()


if __name__ == "__main__":
    main()
