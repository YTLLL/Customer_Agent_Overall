#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
u68c0u67e5u73afu5883u53d8u91cfu52a0u8f7du60c5u51b5
"""

import os
import sys
from dotenv import load_dotenv

# u6dfbu52a0u9879u76eeu6839u76eeu5f55u5230Pythonu8defu5f84
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# u6253u5370u5f53u524du5de5u4f5cu76eeu5f55
print(f"u5f53u524du5de5u4f5cu76eeu5f55: {os.getcwd()}")

# u67e5u627e.envu6587u4ef6
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
print(f".envu6587u4ef6u8defu5f84: {env_path}")
print(f".envu6587u4ef6u662fu5426u5b58u5728: {os.path.exists(env_path)}")

# u52a0u8f7du73afu5883u53d8u91cf
load_dotenv(env_path)

# u68c0u67e5u5173u952eu73afu5883u53d8u91cf
env_vars = [
    "DASHSCOPE_API_KEY",
    "API_HOST",
    "API_PORT",
    "MONGODB_URI",
    "MONGODB_DB_NAME"
]

print("\nu73afu5883u53d8u91cfu68c0u67e5:")
for var in env_vars:
    value = os.getenv(var)
    if value:
        # u5982u679cu662fAPIu5bc6u94a5uff0cu53eau663eu793au524d10u4e2au5b57u7b26
        if "API_KEY" in var and len(value) > 10:
            print(f"  {var}: {value[:10]}...")
        else:
            print(f"  {var}: {value}")
    else:
        print(f"  {var}: u672au8bbeu7f6e")

# u68c0u67e5Pythonu73afu5883
print("\nPythonu73afu5883u4fe1u606f:")
print(f"  Pythonu7248u672c: {sys.version}")
print(f"  Pythonu8defu5f84: {sys.executable}")

# u68c0u67e5condau73afu5883
conda_env = os.getenv("CONDA_DEFAULT_ENV")
print(f"  Condau73afu5883: {conda_env or 'u672au68c0u6d4bu5230'}")
