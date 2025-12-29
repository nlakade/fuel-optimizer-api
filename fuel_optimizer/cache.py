def safe_cache_key(key, key_prefix, version):
    
    safe_key = str(key).replace(':', '_').replace(' ', '_').replace(',', '_')
    return f"{key_prefix}:{version}:{safe_key}"