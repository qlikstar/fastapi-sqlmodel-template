# Database Migrations with Alembic

This directory contains database migration scripts managed by Alembic. These migrations allow you to evolve your database schema over time while preserving existing data.

## Configuration

The database connection is configured through the `.env` file in the project root. The key settings that affect migrations are:

```
# DB_ENGINE can be "sqlite" or "postgres" 
DB_ENGINE="sqlite"  # or "postgres"

# For PostgreSQL
POSTGRES_USER="your_username"
POSTGRES_PASSWORD="your_password"
POSTGRES_SERVER="your_server"
POSTGRES_PORT=5432
POSTGRES_DB="your_database"
```

## Switching Between SQLite and PostgreSQL

### Using SQLite (Development/Testing)

1. In your `.env` file, set:
   ```
   DB_ENGINE="sqlite"
   ```

2. No additional configuration is needed for SQLite, as it will create a local file database.

### Using PostgreSQL (Production)

1. In your `.env` file, set:
   ```
   DB_ENGINE="postgres"
   ```

2. Configure your PostgreSQL connection details:
   ```
   POSTGRES_USER="your_username"
   POSTGRES_PASSWORD="your_password"
   POSTGRES_SERVER="your_server"
   POSTGRES_PORT=5432  # Default PostgreSQL port
   POSTGRES_DB="your_database"
   ```

3. **Important Note for Supabase Users**: 
   - If using Supabase with PgBouncer, use port 5432 (session pooler) instead of 6543 (transaction pooler)
   - The session pooler supports prepared statements which are required by SQLAlchemy

## Migration Commands

All commands should be run from the `src` directory.

### Creating a New Migration

To create a new migration after changing your SQLModel models:

```bash
cd src
python -m alembic revision --autogenerate -m "Description of changes"
```

This will:
1. Compare your SQLModel models with the current database state
2. Generate a new migration script in the `versions` directory

### Applying Migrations

To apply all pending migrations:

```bash
cd src
python -m alembic upgrade head
```

To apply migrations up to a specific version:

```bash
cd src
python -m alembic upgrade <revision_id>
```

### Reverting Migrations

To revert the most recent migration:

```bash
cd src
python -m alembic downgrade -1
```

To revert to a specific version:

```bash
cd src
python -m alembic downgrade <revision_id>
```

To revert all migrations:

```bash
cd src
python -m alembic downgrade base
```

### Checking Migration Status

To see which migrations have been applied and which are pending:

```bash
cd src
python -m alembic current  # Shows current revision
python -m alembic history  # Shows migration history
```

## Troubleshooting

### PostgreSQL Connection Issues

If you encounter issues connecting to PostgreSQL:

1. Verify your connection details in the `.env` file
2. For Supabase users, ensure you're using the session pooler (port 5432)
3. Check that your database user has the necessary permissions
4. If using SSL, ensure your SSL settings are correctly configured

### SQLite Issues

SQLite migrations are typically simpler but have limitations:

1. Some column type changes may not be supported
2. Ensure your application has write permissions to the SQLite database file
3. SQLite doesn't support all PostgreSQL features (like certain constraint types)

## Best Practices

1. Always backup your database before running migrations in production
2. Test migrations on a staging environment first
3. Keep migrations small and focused on specific changes
4. Add clear comments to your migration scripts
5. Include both upgrade and downgrade paths in your migrations