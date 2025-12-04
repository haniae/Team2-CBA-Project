# Additional Fix: Import-Time Directory Creation

## Issue Found

After the initial fix, I discovered another critical import-time operation that causes `FUNCTION_INVOCATION_FAILED` in Vercel's serverless environment.

### The Problem

In `src/finanlyzeos_chatbot/web.py` (line 248), there was:

```python
CHARTS_DIR = (BASE_DIR / "charts").resolve()
CHARTS_DIR.mkdir(exist_ok=True)  # ← FAILS in serverless!
```

**Why this fails:**
- Executes at **import time** (when module is loaded)
- Serverless file systems are **read-only** or have **limited write access**
- Directory creation requires **write permissions** that may not exist
- Causes `FUNCTION_INVOCATION_FAILED` before any request is handled

## The Fix

### Before (Import-Time - FAILS)
```python
CHARTS_DIR = (BASE_DIR / "charts").resolve()
CHARTS_DIR.mkdir(exist_ok=True)  # Runs during import!
```

### After (Lazy Creation - WORKS)
```python
CHARTS_DIR = (BASE_DIR / "charts").resolve()

def ensure_charts_dir():
    """Ensure CHARTS_DIR exists. Safe for serverless environments."""
    try:
        CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        # In serverless environments, directory creation may fail
        # This is OK if we're only reading charts, not writing them
        LOGGER.warning(f"Could not create charts directory {CHARTS_DIR}: {e}. "
                      "Chart writing may be disabled in this environment.")
```

## Key Changes

1. **Removed import-time `mkdir()`** - No longer creates directory during module import
2. **Added lazy creation function** - Directory is only created when actually needed
3. **Added error handling** - Gracefully handles permission errors in serverless
4. **Added logging** - Warns if directory creation fails (but doesn't crash)

## When to Use `ensure_charts_dir()`

Call this function **only when writing charts**, not during import:

```python
# When writing a chart file:
def save_chart(chart_id: str, chart_data: bytes):
    ensure_charts_dir()  # Create directory only when needed
    chart_path = CHARTS_DIR / f"{chart_id}.html"
    chart_path.write_bytes(chart_data)
```

**Note:** Reading charts doesn't require the directory to exist - the endpoint checks `if html_path.exists()` which is safe.

## Why This Pattern Matters

### Serverless File System Constraints

```
┌─────────────────────────────────────┐
│  Local Development                  │
│  ✅ Full read/write access          │
│  ✅ Can create directories           │
│  ✅ Persistent file system          │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Vercel Serverless                   │
│  ⚠️  Read-only file system          │
│  ⚠️  Limited write access (/tmp)    │
│  ⚠️  Ephemeral storage               │
│  ⚠️  No persistent directories       │
└─────────────────────────────────────┘
```

### Import-Time vs Runtime Operations

**❌ BAD - Import-Time (Fails in Serverless):**
```python
# Module-level code runs during import
CHARTS_DIR.mkdir(exist_ok=True)  # ← Fails if no write access
DATABASE.connect()  # ← Fails if DB unavailable
CONFIG_FILE.read_text()  # ← Fails if file missing
```

**✅ GOOD - Lazy/Runtime (Works in Serverless):**
```python
# Functions called only when needed
def ensure_charts_dir():
    try:
        CHARTS_DIR.mkdir(exist_ok=True)
    except (OSError, PermissionError):
        pass  # Handle gracefully

def get_db():
    if not hasattr(get_db, '_conn'):
        get_db._conn = DATABASE.connect()
    return get_db._conn
```

## Additional Considerations

### For Chart Storage in Serverless

If you need to **write charts** in a serverless environment, consider:

1. **Use `/tmp` directory** (temporary, cleared between invocations):
   ```python
   import tempfile
   CHARTS_DIR = Path(tempfile.gettempdir()) / "charts"
   ```

2. **Use cloud storage** (S3, Cloud Storage, etc.):
   ```python
   # Upload charts to S3/Cloud Storage instead of local filesystem
   s3_client.upload_file(chart_path, bucket, key)
   ```

3. **Generate charts on-demand** (don't persist):
   ```python
   # Generate chart HTML in memory, return directly
   return Response(content=chart_html, media_type="text/html")
   ```

## Testing the Fix

1. **Deploy to Vercel** - The function should now import successfully
2. **Check logs** - Look for any warnings about directory creation
3. **Test chart endpoints** - Verify chart reading still works
4. **Test chart writing** (if applicable) - Verify lazy creation works

## Summary

- ✅ **Fixed**: Removed import-time directory creation
- ✅ **Added**: Lazy directory creation with error handling
- ✅ **Result**: Function can now import successfully in serverless environment
- ⚠️ **Note**: Chart writing may need additional changes for full serverless support

