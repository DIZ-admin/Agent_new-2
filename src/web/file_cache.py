"""
File Cache Module

This module provides caching functionality for file operations.
"""

import time
from collections import OrderedDict
from threading import RLock
from src.utils.logging import get_logger

# Get logger
logger = get_logger('web.file_cache')


class LRUCache:
    """
    Thread-safe LRU (Least Recently Used) cache implementation.
    
    This cache has a fixed maximum size and will evict the least recently used
    items when the size limit is reached.
    """
    
    def __init__(self, max_size=1000, ttl=3600):
        """
        Initialize the LRU cache.
        
        Args:
            max_size (int): Maximum number of items in the cache
            ttl (int): Time to live in seconds (default: 1 hour)
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl
        self.lock = RLock()
        self.hits = 0
        self.misses = 0
        
    def get(self, key):
        """
        Get an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
                
            # Check if item has expired
            item, timestamp = self.cache[key]
            if self.ttl > 0 and time.time() - timestamp > self.ttl:
                del self.cache[key]
                self.misses += 1
                return None
                
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return item
            
    def set(self, key, value):
        """
        Add or update an item in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            None
        """
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                
            self.cache[key] = (value, time.time())
            
            # Evict oldest items if over size limit
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
                
    def delete(self, key):
        """
        Remove an item from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if item was removed, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
            
    def clear(self):
        """
        Clear all items from the cache.
        
        Returns:
            None
        """
        with self.lock:
            self.cache.clear()
            
    def get_stats(self):
        """
        Get cache statistics.
        
        Returns:
            dict: Cache statistics
        """
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total) * 100 if total > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate
            }


# Create global file cache instance
file_cache = LRUCache(max_size=1000, ttl=300)  # 5 minute TTL


def get_file_cache():
    """
    Get the global file cache instance.
    
    Returns:
        LRUCache: Global file cache instance
    """
    return file_cache
