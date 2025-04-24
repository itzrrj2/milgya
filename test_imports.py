#!/usr/bin/env python3
"""
Test script to verify that all required modules can be properly imported.
"""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all necessary modules can be imported."""
    imports = {
        "pyrogram": "Telegram API client",
        "motor.motor_asyncio": "MongoDB async driver",
        "pymongo": "MongoDB driver",
        "flask": "Web server for keep-alive",
        "aria2p": "Aria2 RPC client for downloads",
        "shortzy": "Link shortener",
        "dotenv": "Environment variable loader"
    }
    
    success = True
    logger.info("Testing import of required modules...")
    
    for module, description in imports.items():
        try:
            __import__(module)
            logger.info(f"✅ Successfully imported {module} ({description})")
        except ImportError as e:
            logger.error(f"❌ Failed to import {module} ({description}): {e}")
            success = False
    
    return success

if __name__ == "__main__":
    if test_imports():
        logger.info("All imports successful! ✨")
    else:
        logger.error("Some imports failed. Please check the requirements. ❌") 