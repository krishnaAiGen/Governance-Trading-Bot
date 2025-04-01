#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to download trading models from Google Drive.
"""

import os
import sys
import subprocess
import platform
import tempfile
import shutil

def create_directories():
    """Create the necessary directories for the models."""
    os.makedirs('trained_model/bullish', exist_ok=True)
    os.makedirs('trained_model/bearish', exist_ok=True)
    os.makedirs('trained_model/sentiment', exist_ok=True)
    print("Created model directories.")

def check_requirements():
    """Check if the required tools are installed."""
    try:
        # Check if gdown is installed
        subprocess.run(['pip', 'show', 'gdown'], 
                      check=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Installing gdown...")
        subprocess.run(['pip', 'install', 'gdown'])
    
    # Check if unzip is installed (for Linux/MacOS)
    if platform.system() != "Windows":
        try:
            subprocess.run(['which', 'unzip'], 
                          check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            print("Error: 'unzip' is not installed. Please install it.")
            if platform.system() == "Linux":
                print("You can install it with: sudo apt-get install unzip")
            elif platform.system() == "Darwin":  # MacOS
                print("You can install it with: brew install unzip")
            sys.exit(1)

def download_models():
    """Download the models from Google Drive."""
    print("Downloading trading models...")
    # Define the Google Drive file ID for the model zip file
    file_id = "1bT6gt61GtOXnnyVYOsMTZmkAgxosVijM"
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the zip file
        try:
            zip_path = os.path.join(temp_dir, "trading_models.zip")
            subprocess.run(
                ['gdown', f'https://drive.google.com/uc?id={file_id}', 
                 '-O', zip_path],
                check=True
            )
            print("Models downloaded successfully.")
            
            # Extract the zip file
            extract_dir = os.path.join(temp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            
            print("Extracting models...")
            if platform.system() == "Windows":
                # Use Python's zipfile for Windows
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                # Use unzip command for Linux/MacOS
                subprocess.run(['unzip', zip_path, '-d', extract_dir], check=True)
            
            # Copy the extracted files to the appropriate directories
            print("Copying model files to target directories...")
            for model_type in ['bullish', 'bearish', 'sentiment']:
                source_dir = os.path.join(extract_dir, model_type)
                target_dir = os.path.join('trained_model', model_type)
                
                if os.path.exists(source_dir):
                    # Copy all files from source to target
                    for item in os.listdir(source_dir):
                        s = os.path.join(source_dir, item)
                        d = os.path.join(target_dir, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)
            
            print("Model files copied successfully.")
            return
        except subprocess.CalledProcessError as e:
            print(f"Error downloading models: {e}")
            print("Please download the models manually from the Google Drive link.")
            print("https://drive.google.com/file/d/1bT6gt61GtOXnnyVYOsMTZmkAgxosVijM/view?usp=sharing")

def verify_installation():
    """Verify that the models were correctly installed."""
    all_good = True
    for model_dir in ['bullish', 'bearish', 'sentiment']:
        path = os.path.join('trained_model', model_dir)
        if not os.path.exists(path) or not os.listdir(path):
            print(f"Warning: {path} is empty or does not exist.")
            all_good = False
    
    if all_good:
        print("Model installation verified successfully!")
    else:
        print("Some model directories are empty or missing.")
        print("Please download the models manually from the Google Drive link.")
        print("https://drive.google.com/file/d/1bT6gt61GtOXnnyVYOsMTZmkAgxosVijM/view?usp=sharing")

def main():
    """Main function."""
    print("Trading Models Downloader")
    print("========================")
    
    create_directories()
    check_requirements()
    download_models()
    verify_installation()
    
    print("\nDownload process completed.")
    print("If the models were not downloaded correctly, please download them manually from:")
    print("https://drive.google.com/file/d/1bT6gt61GtOXnnyVYOsMTZmkAgxosVijM/view?usp=sharing")

if __name__ == "__main__":
    main() 