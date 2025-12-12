# Trace where parties table is being defined
import sqlalchemy.sql.schema
import sys

original_new = sqlalchemy.sql.schema.Table.__new__
call_count = 0

def traced_new(cls, *args, **kw):
    global call_count
    call_count += 1
    if args and args[0] == 'parties':
        import traceback
        print(f"\n=== PARTIES TABLE DEFINITION #{call_count} ===")
        traceback.print_stack(limit=15)
        sys.stdout.flush()
    return original_new(cls, *args, **kw)

sqlalchemy.sql.schema.Table.__new__ = staticmethod(traced_new)

# Now import
try:
    from app.models.models import PartyType
    print("\n✓ Models imported successfully!")
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
