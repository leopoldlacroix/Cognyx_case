"""
CLI entry point for Cognyx BOM Reuse Explorer.
"""
import argparse
import sys
from pathlib import Path

from app.db.connection import init_database
from app.services.ingestion import ingest_all_files, get_ingestion_status


def main():
    parser = argparse.ArgumentParser(description='Cognyx BOM Reuse Explorer CLI')
    parser.add_argument('--db', default='cognyx.db', help='Database path')
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest all source files')
    ingest_parser.add_argument('--file', help='Single file to ingest (path)')
    ingest_parser.add_argument('--system', help='Source system for single file')
    ingest_parser.add_argument('--db', help='Database path for this command')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show ingestion status')
    status_parser.add_argument('--db', help='Database path for this command')

    args = parser.parse_args()

    db_path = args.db or 'cognyx.db'
    conn = init_database(db_path)

    if args.command == 'ingest':
        if args.file and args.system:
            # Ingest single file
            from app.services.ingestion import ingest_csv_file, compute_file_hash, register_source_file
            from datetime import datetime, timezone
            
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {args.file}")
                sys.exit(1)
            
            file_hash = compute_file_hash(file_path)
            ingested_at = datetime.now(timezone.utc)
            source_file_id = register_source_file(conn, args.system, file_path.name, file_hash, ingested_at)
            
            print(f"Ingested {file_path.name} ({args.system}) - source_file_id: {source_file_id}")
        else:
            # Ingest all files
            base_path = Path('/home/leopold-lacroix/Desktop/Projects/Cognyx/data/inputs')
            summary = ingest_all_files(conn, base_path)
            
            print("\n=== Ingestion Summary ===")
            for f in summary['files']:
                print(f"  {f['file_name']}: {f['row_count']} rows, {f['quarantined_count']} quarantined")
            print(f"\nTotal: {summary['total_rows']} rows, {summary['total_quarantined']} quarantined")
    
    elif args.command == 'status':
        status = get_ingestion_status(conn)
        
        print("\n=== Source File Status ===")
        print(f"{'FILE':<25} {'SYSTEM':<12} {'ROWS':<8}")
        print("-" * 50)
        for row in status:
            print(f"{row['file_name']:<25} {row['source_system']:<12} {row['bom_lines'] or 0 + row['assemblies'] or 0 + row['variants'] or 0 + row['materials'] or 0 + row['suppliers'] or 0 + row['notes'] or 0:<8}")


if __name__ == '__main__':
    main()
