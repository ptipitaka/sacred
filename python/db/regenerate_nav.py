#!/usr/bin/env python3
"""
Simple script to regenerate navigation file only
"""
from build_tree import TipitakaBuilder

if __name__ == "__main__":
    builder = TipitakaBuilder()
    
    # Connect to database
    print("Connecting to database...")
    builder.connect_database()
    
    # Generate navigation file with max_level = 0
    print("Generating navigation file with max_level = 0...")
    sidebar_data = builder._build_sidebar_data(max_level=0)
    builder._write_navigation_file(sidebar_data)
    
    print("Navigation file regenerated successfully!")
