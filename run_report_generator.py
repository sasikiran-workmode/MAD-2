#!/usr/bin/env python3
"""
Evidence-MAD Project Report Generator — Master Script
Assembles all 7 parts into a single execution
"""

# Read and concatenate all parts, then exec them sharing the same namespace
import sys, os

part_files = [
    "generate_report.py",
    "generate_report_p2.py",
    "generate_report_p3.py",
    "generate_report_p4.py",
    "generate_report_p5.py",
    "generate_report_p6.py",
    "generate_report_p7.py",
]

base_dir = os.path.dirname(os.path.abspath(__file__))
namespace = {}

for pf in part_files:
    path = os.path.join(base_dir, pf)
    print(f"[+] Loading {pf} ...")
    with open(path, "r") as f:
        code = f.read()
    exec(compile(code, path, "exec"), namespace)

print("\n✓ All parts executed successfully.")
