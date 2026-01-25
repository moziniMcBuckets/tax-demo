# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Common utilities for Gateway Lambda tools.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger()


def parse_iso_date(date_string: str) -> datetime:
    """
    Parse ISO format date string to datetime.
    
    Args:
        date_string: ISO format date string
    
    Returns:
        datetime object
    """
    return datetime.fromisoformat(date_string.replace('Z', '+00:00'))


def format_date_for_display(date_string: str) -> str:
    """
    Format ISO date string for human-readable display.
    
    Args:
        date_string: ISO format date string
    
    Returns:
        Formatted date string (YYYY-MM-DD)
    """
    try:
        dt = parse_iso_date(date_string)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return date_string


def calculate_days_between(start_date: str, end_date: str) -> int:
    """
    Calculate days between two ISO date strings.
    
    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    
    Returns:
        Number of days between dates
    """
    try:
        start = parse_iso_date(start_date)
        end = parse_iso_date(end_date)
        return (end - start).days
    except Exception as e:
        logger.error(f"Error calculating days between dates: {e}")
        return 0


def extract_tool_name(context: Any) -> str:
    """
    Extract tool name from Lambda context.
    
    Args:
        context: Lambda context object
    
    Returns:
        Tool name without target prefix
    """
    delimiter = "___"
    original_tool_name = context.client_context.custom['bedrockAgentCoreToolName']
    
    if delimiter in original_tool_name:
        return original_tool_name[original_tool_name.index(delimiter) + len(delimiter):]
    
    return original_tool_name


def build_error_response(error: Exception) -> Dict[str, Any]:
    """
    Build standardized error response.
    
    Args:
        error: Exception object
    
    Returns:
        Error response dictionary
    """
    return {
        'content': [
            {
                'type': 'text',
                'text': json.dumps({
                    'success': False,
                    'error': str(error),
                    'error_type': type(error).__name__,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        ]
    }


def build_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build standardized success response.
    
    Args:
        data: Response data dictionary
    
    Returns:
        Success response dictionary
    """
    return {
        'content': [
            {
                'type': 'text',
                'text': json.dumps(data, indent=2)
            }
        ]
    }
