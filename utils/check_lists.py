# Zapret Launcher - Bypass restrictions
# Copyright (C) 2026 trimansberg
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU GPL v3 or any later version.
#
# Distributed WITHOUT ANY WARRANTY.

import re
from utils.languages import tr
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

class ListChecker:
    CHECK_FILES = [
        "list-general.txt",
        "list-custom.txt", 
        "list-google.txt",
        "list-white.txt"
    ]
    
    def __init__(self, lists_dir: Path):
        self.lists_dir = Path(lists_dir)
        self.duplicates: Dict[str, List[str]] = {}
        self.total_domains: Dict[str, int] = {}
        self.unique_domains: Dict[str, int] = {}
        
    def extract_domain(self, line: str) -> str:
        line = line.strip()
        
        if not line or line.startswith('#'):
            return None
        
        domain = line.lower()
        
        if domain.startswith('*.'):
            domain = domain[2:]
        
        if '/' in domain:
            domain = domain.split('/')[0]
        
        if re.match(r'^[a-z0-9\-\.]+\.[a-z]{2,}$', domain):
            return domain
        
        return None
    
    def check_file(self, file_path: Path) -> Tuple[Dict[str, List[int]], int, int]:
        if not file_path.exists():
            return {}, 0, 0
        
        domains = defaultdict(list)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    domain = self.extract_domain(line)
                    if domain:
                        domains[domain].append(line_num)
        except Exception:
            return {}, 0, 0
        
        duplicates = {
            domain: lines 
            for domain, lines in domains.items() 
            if len(lines) > 1
        }
        
        return duplicates, len(domains), len([d for d in domains if len(domains[d]) == 1])
    
    def check_all_files(self) -> Dict[str, Dict]:
        results = {}
        
        for filename in self.CHECK_FILES:
            file_path = self.lists_dir / filename
            duplicates, total, unique = self.check_file(file_path)
            
            results[filename] = {
                'duplicates': duplicates,
                'total': total,
                'unique': unique
            }
        
        return results
    
    def has_duplicates(self, results: Dict[str, Dict]) -> bool:
        for data in results.values():
            if data['duplicates']:
                return True
        return False
    
    def get_duplicates_summary(self, results: Dict[str, Dict]) -> str:
        summary_lines = []
        
        for filename, data in results.items():
            if data['duplicates']:
                summary_lines.append(f"\n— {filename}:")
                summary_lines.append(f"   {tr('duplicates_total')}: {data['total']}")
                summary_lines.append(f"   {tr('duplicates_unique')}: {data['unique']}")
                summary_lines.append(f"   {tr('duplicates_count')}: {len(data['duplicates'])}")
                
                for domain, lines in data['duplicates'].items():
                    lines_str = ', '.join(map(str, lines))
                    summary_lines.append(f"   • {domain} ({tr('duplicates_lines')}: {lines_str})")
        
        return '\n'.join(summary_lines) if summary_lines else ""

def check_lists_for_duplicates(lists_dir: Path) -> Tuple[bool, str]:
    checker = ListChecker(lists_dir)
    results = checker.check_all_files()
    
    if checker.has_duplicates(results):
        summary = checker.get_duplicates_summary(results)
        return True, summary
    
    return False, ""
