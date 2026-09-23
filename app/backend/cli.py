"""
CLI entry point for Cognyx BOM Reuse Explorer.
"""
import argparse
import json
import sys
from pathlib import Path

from app.db.connection import init_database
from app.services.ingestion import ingest_all_files, get_ingestion_status, get_quarantine_count

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DEFAULT_INPUTS = REPO_ROOT / "data" / "inputs"


def main():
    parser = argparse.ArgumentParser(description='Cognyx BOM Reuse Explorer CLI')
    parser.add_argument('--db', default='cognyx.db', help='Database path')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest all source files')
    ingest_parser.add_argument('--file', help='Single file to ingest (path)')
    ingest_parser.add_argument('--system', help='Source system for single file')
    ingest_parser.add_argument('--db', help='Database path for this command')
    ingest_parser.add_argument(
        '--inputs',
        help='Directory containing PLM/ERP/engineering CSVs',
        default=str(DEFAULT_INPUTS),
    )

    # Status command
    status_parser = subparsers.add_parser('status', help='Show ingestion status')
    status_parser.add_argument('--db', help='Database path for this command')

    # One-page client report
    report_parser = subparsers.add_parser('report', help='Write a one-page HTML reuse snapshot')
    report_parser.add_argument('--db', help='Database path for this command')
    report_parser.add_argument('--output', help='HTML file to write')

    # Review: list / decide
    review_parser = subparsers.add_parser('review', help='List or decide reconciliations')
    review_sub = review_parser.add_subparsers(dest='review_command', required=True)

    list_parser = review_sub.add_parser('list', help='List reconciliation proposals')
    list_parser.add_argument('--entity', required=True, choices=['component', 'assembly', 'supplier'])
    list_parser.add_argument('--status', default=None)
    list_parser.add_argument(
        '--confidence',
        dest='confidence_band',
        choices=['uncertain', 'likely', 'strong', 'weak'],
        default=None,
    )
    list_parser.add_argument('--method', default=None)
    list_parser.add_argument('--source', dest='source_system', choices=['PLM', 'ERP'], default=None)
    list_parser.add_argument(
        '--relationship',
        choices=['identity', 'functional_similarity', 'variant_specific'],
        default=None,
    )
    list_parser.add_argument('--db', help='Database path for this command')

    decide_parser = review_sub.add_parser('decide', help='Accept, reject, or redirect a proposal')
    decide_parser.add_argument('--entity', required=True, choices=['component', 'assembly', 'supplier'])
    decide_parser.add_argument('--id', type=int, required=True, dest='reconciliation_id')
    decide_parser.add_argument('--action', required=True, choices=['accept', 'reject', 'redirect'])
    decide_parser.add_argument('--rationale', default=None)
    decide_parser.add_argument('--redirect-to', type=int, default=None, dest='redirect_to')
    decide_parser.add_argument('--reviewer', default='operator')
    decide_parser.add_argument('--db', help='Database path for this command')

    # Analyze: reuse | candidates | blockers | quality
    analyze_parser = subparsers.add_parser('analyze', help='Write analysis JSON reports')
    analyze_parser.add_argument(
        'report_kind',
        choices=['reuse', 'candidates', 'blockers', 'quality'],
        help='Which report to write',
    )
    analyze_parser.add_argument('--db', help='Database path for this command')

    args = parser.parse_args()

    db_path = args.db or 'cognyx.db'
    if args.command == 'report' and db_path == 'cognyx.db':
        db_path = str(PROCESSED_DIR / 'cognyx.db')
    conn = init_database(db_path)

    if args.command == 'ingest':
        if args.file and args.system:
            from app.services.ingestion import compute_file_hash, register_source_file
            from datetime import datetime, timezone

            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {args.file}")
                sys.exit(1)

            file_hash = compute_file_hash(file_path)
            ingested_at = datetime.now(timezone.utc)
            source_file_id = register_source_file(
                conn, args.system, file_path.name, file_hash, ingested_at
            )

            print(f"Ingested {file_path.name} ({args.system}) - source_file_id: {source_file_id}")
        else:
            base_path = Path(args.inputs)
            if not base_path.is_dir():
                print(f"Error: input folder not found: {base_path}")
                sys.exit(1)
            summary = ingest_all_files(conn, base_path)

            print("\n=== Ingestion Summary ===")
            for f in summary['files']:
                print(
                    f"  {f['file_name']}: {f['row_count']} rows, "
                    f"{f['quarantined_count']} quarantined"
                )
            print(
                f"\nTotal: {summary['total_rows']} rows, "
                f"{summary['total_quarantined']} quarantined"
            )

    elif args.command == 'status':
        status = get_ingestion_status(conn)

        print("\n=== Source File Status ===")
        print(f"{'FILE':<25} {'SYSTEM':<12} {'ROWS':<8} {'QUARANTINED':<12}")
        print("-" * 60)
        for row in status:
            qcount = get_quarantine_count(conn) if not hasattr(row, 'quarantine_count') else 0
            total = (
                (row['bom_lines'] or 0)
                + (row['assemblies'] or 0)
                + (row['variants'] or 0)
                + (row['materials'] or 0)
                + (row['suppliers'] or 0)
                + (row['notes'] or 0)
            )
            print(f"{row['file_name']:<25} {row['source_system']:<12} {total:<8} {qcount:<12}")

    elif args.command == 'report':
        from app.services.html_pages import write_site
        from app.services.report import prepare_database

        inputs_dir = DEFAULT_INPUTS
        if not inputs_dir.is_dir():
            print(f"Error: input folder not found: {inputs_dir}")
            sys.exit(1)
        output_dir = (
            Path(args.output).resolve().parent if args.output else PROCESSED_DIR
        )
        prepare_database(conn, inputs_dir)
        written = write_site(conn, output_dir)
        for path in written:
            print(f"Wrote {path}")
        print(f"Open {output_dir / 'workflow.html'} in a browser.")

    elif args.command == 'review':
        from app.services.review import decide_reconciliation, list_reconciliations

        if args.review_command == 'list':
            result = list_reconciliations(
                conn,
                entity_type=args.entity,
                status=args.status,
                confidence_band=args.confidence_band,
                method=args.method,
                source_system=args.source_system,
                relationship=args.relationship,
            )
            print(json.dumps(result, indent=2, default=str))
            print(f"count: {result['count']}")
        elif args.review_command == 'decide':
            updated = decide_reconciliation(
                conn,
                entity_type=args.entity,
                reconciliation_id=args.reconciliation_id,
                action=args.action,
                rationale=args.rationale,
                redirect_source_id=args.redirect_to,
                decided_by=args.reviewer,
            )
            print(json.dumps(updated, indent=2, default=str))

    elif args.command == 'analyze':
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        kind = args.report_kind

        if kind == 'reuse':
            from app.services.analysis import already_reused
            from app.services.canonicalization import build_canonical_model

            build_canonical_model(conn)
            data = already_reused(conn)
            out_path = PROCESSED_DIR / 'already_reused.json'
        elif kind == 'candidates':
            from app.services.analysis import reusable_candidates

            data = reusable_candidates(conn)
            out_path = PROCESSED_DIR / 'reusable_candidates.json'
        elif kind == 'blockers':
            from app.services.quality import blockers

            data = blockers(conn)
            out_path = PROCESSED_DIR / 'blockers.json'
        else:
            from app.services.quality import data_quality_issues

            data = data_quality_issues(conn)
            out_path = PROCESSED_DIR / 'data_quality.json'

        out_path.write_text(json.dumps(data, indent=2, default=str), encoding='utf-8')
        if isinstance(data, list):
            count = len(data)
        elif isinstance(data, dict) and 'issues' in data:
            count = len(data['issues'])
        else:
            count = 1
        print(f"{out_path} ({count} rows)")


if __name__ == '__main__':
    main()
