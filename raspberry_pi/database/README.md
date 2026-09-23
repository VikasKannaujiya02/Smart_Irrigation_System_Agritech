# SQLite Database

Owns SQLite schema, migrations, repositories, transactions, and database error handling for telemetry, commands, alerts, predictions, analytics, and state.

Implemented files:

- `database.py`: Database facade for migrations, repositories, backup, and integrity checks.
- `connection.py`: SQLite connection pool and transaction handling.
- `schema.py`: Versioned schema definition.
- `schema.sql`: SQL schema file.
- `migration.py`: Schema migration runner.
- `repository.py`: Repository classes for all database tables.
- `backup.py`: Backup, restore, latest backup lookup, and integrity check utilities.
- `database_manager.py`: Application-level database lifecycle manager.
- `query_builder.py`: Safe parameterized query builder helpers.

Documentation:

- `docs/DATABASE_LAYER.md`
