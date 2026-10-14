"""Inspect the tables, columns, relationships, and row counts in Chinook."""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "chinook.db"


def inspect_schema():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        total_rows = 0

        print(f"Database: {DATABASE_PATH}")
        print(f"Number of tables: {len(tables)}")

        for (table_name,) in tables:
            # Table names come from SQLite's own schema.
            columns = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            row_count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            total_rows += row_count

            print(f"\nTable: {table_name}")
            print(f"Rows: {row_count}")
            print("Columns:")

            for column in columns:
                name = column[1]
                data_type = column[2]
                primary_key = " PRIMARY KEY" if column[5] else ""
                print(f"  - {name} ({data_type}){primary_key}")

            foreign_keys = connection.execute(
                f'PRAGMA foreign_key_list("{table_name}")'
            ).fetchall()

            for foreign_key in foreign_keys:
                print(
                    f"  Foreign key: {foreign_key[3]} -> "
                    f"{foreign_key[2]}.{foreign_key[4]}"
                )

        print(f"\nTotal rows across all tables: {total_rows}")

    finally:
        connection.close()


if __name__ == "__main__":
    inspect_schema()