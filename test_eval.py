import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import run_pipeline

async def main():
    print("Testing pipeline logic...")
    # Just checking what happens when we don't actually run video collection
    
if __name__ == '__main__':
    print("Done")
