#!/usr/bin/env python3
"""
API Integration Utilities Module

This module provides base classes and utilities for API integrations.
"""

import time
import functools
from typing import Any, Callable, Dict, Optional, TypeVar, Union, List
import logging

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def retry(
    max_attempts: int = 3, 
    retry_delay: int = 1, 
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        retry_delay (int): Initial delay between retries (in seconds)
        backoff_factor (float): Multiplier for the delay on each retry
        exceptions (tuple): Exceptions to catch and retry
        
    Returns:
        Callable: Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            delay = retry_delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"Max retry attempts ({max_attempts}) reached for {func.__name__}: {str(e)}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} for {func.__name__} failed: {str(e)}. "
                        f"Retrying in {delay} seconds..."
                    )
                    
                    time.sleep(delay)
                    delay *= backoff_factor
                    attempt += 1
        
        return wrapper
    
    return decorator


class APIRateLimiter:
    """
    Rate limiter for API calls to prevent exceeding rate limits.
    """
    
    def __init__(self, calls_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute (int): Maximum number of calls allowed per minute
        """
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute  # minimum interval between calls in seconds
        self.last_call_time = 0.0
    
    def wait_if_needed(self) -> None:
        """
        Wait if necessary to comply with rate limits.
        """
        current_time = time.time()
        elapsed = current_time - self.last_call_time
        
        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        self.last_call_time = time.time()
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting to a function.
        
        Args:
            func (Callable): Function to decorate
            
        Returns:
            Callable: Rate-limited function
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        
        return wrapper


class CacheManager:
    """
    Simple in-memory cache manager.
    """
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        """
        Initialize cache manager.
        
        Args:
            max_size (int): Maximum number of items in cache
            ttl (int): Time to live for cache items in seconds
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get item from cache if it exists and is not expired.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[Any]: Cached value or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        expiry_time = item['timestamp'] + self.ttl
        
        if time.time() > expiry_time:
            # Item has expired
            del self.cache[key]
            return None
        
        return item['value']
    
    def set(self, key: str, value: Any) -> None:
        """
        Set item in cache.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
        """
        # If cache is full, remove oldest item
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to cache function results.
        
        Args:
            func (Callable): Function to decorate
            
        Returns:
            Callable: Function with caching
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            key = ":".join(key_parts)
            
            # Check cache
            cached_value = self.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {key}")
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            self.set(key, result)
            logger.debug(f"Cache miss for {key}, result cached")
            
            return result
        
        return wrapper


class APIClientBase:
    """
    Base class for API clients with retry, rate limiting, and caching.
    """
    
    def __init__(
        self, 
        base_url: str,
        api_key: Optional[str] = None,
        rate_limit: int = 60,
        max_retries: int = 3,
        retry_delay: int = 1,
        cache_size: int = 100,
        cache_ttl: int = 3600
    ):
        """
        Initialize API client.
        
        Args:
            base_url (str): Base URL for API
            api_key (Optional[str]): API key
            rate_limit (int): Maximum calls per minute
            max_retries (int): Maximum number of retry attempts
            retry_delay (int): Initial delay between retries (in seconds)
            cache_size (int): Maximum number of items in cache
            cache_ttl (int): Time to live for cache items in seconds
        """
        self.base_url = base_url
        self.api_key = api_key
        self.rate_limiter = APIRateLimiter(rate_limit)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cache = CacheManager(cache_size, cache_ttl)
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests.
        
        Returns:
            Dict[str, str]: Headers dictionary
        """
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        return headers
    
    @retry(max_attempts=3, retry_delay=1)
    @APIRateLimiter(calls_per_minute=60)
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an API request with retry and rate limiting.
        This method should be implemented by subclasses.
        
        Args:
            method (str): HTTP method
            endpoint (str): API endpoint
            **kwargs: Additional arguments for the request
            
        Returns:
            Any: API response
            
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement _make_request method")


# For direct testing
if __name__ == "__main__":
    # Test retry decorator
    @retry(max_attempts=3, retry_delay=0.1)
    def test_retry_function(succeed_on_attempt):
        global current_attempt
        current_attempt += 1
        if current_attempt < succeed_on_attempt:
            raise ValueError(f"Failing on attempt {current_attempt}")
        return "Success!"
    
    # Test succeeding on third attempt
    current_attempt = 0
    try:
        result = test_retry_function(3)
        print(f"Result after retries: {result}")
    except ValueError as e:
        print(f"Failed with error: {e}")
    
    # Test rate limiter
    rate_limiter = APIRateLimiter(calls_per_minute=120)  # Allow 2 calls per second
    
    @rate_limiter
    def rate_limited_function():
        return time.time()
    
    # Test rate limiting
    print("Testing rate limiting...")
    start_time = time.time()
    times = []
    for _ in range(5):
        times.append(rate_limited_function())
    end_time = time.time()
    
    intervals = [times[i] - times[i-1] for i in range(1, len(times))]
    print(f"Intervals between calls: {[round(i, 3) for i in intervals]} seconds")
    print(f"Total time for 5 calls: {end_time - start_time:.2f} seconds")
    
    # Test cache manager
    cache = CacheManager(max_size=5, ttl=5)
    
    @cache
    def expensive_function(x):
        print(f"Computing expensive result for {x}...")
        time.sleep(0.1)  # Simulate expensive computation
        return x * 2
    
    # Test caching
    print("\nTesting caching...")
    for i in range(3):
        print(f"Call {i+1} for input 5: {expensive_function(5)}")
        print(f"Call {i+1} for input 10: {expensive_function(10)}")
