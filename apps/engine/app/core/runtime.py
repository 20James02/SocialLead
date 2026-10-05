import asyncio

# Serialize local API transactions with maintenance and scanner writes.
# This also makes online restore exclusive without replacing the WAL file.
operation_lock = asyncio.Lock()
