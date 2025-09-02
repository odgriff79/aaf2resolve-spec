#!/usr/bin/env python3
"""Effect Parameter Analysis Tool"""
import aaf2
import argparse
from collections import defaultdict, Counter
import json

def inventory_all_parameters(aaf_path):
    """Catalog all parameters across all OperationGroups"""
    param_catalog = defaultdict(lambda: {'count': 0, 'values': [], 'types': set()})
    effect_types = defaultdict(int)
    
    with aaf2.open(aaf_path, 'r') as f:
        comp_mobs = [mob for mob in f.content.mobs if 'CompositionMob' in str(type(mob).__name__)]
        comp = comp_mobs[0]
        
        for slot in comp.slots:
            if hasattr(slot, 'segment') and 'Sequence' in str(type(slot.segment).__name__):
                components = list(slot.segment.components)
                for component in components:
                    if 'OperationGroup' in str(type(component).__name__) and hasattr(component, 'parameters'):
                        params = list(component.parameters)
                        for param in params:
                            if hasattr(param, 'name') and hasattr(param, 'value'):
                                name = str(param.name)
                                value = param.value
                                param_catalog[name]['count'] += 1
                                param_catalog[name]['types'].add(str(type(value)))
                                param_catalog[name]['values'].append(value)
                                
                                # Track effect type
                                if name.startswith('AFX_'):
                                    effect_types['AVX2 Effect'] += 1
                                elif name.startswith('DVE_'):
                                    effect_types['Image Effect'] += 1
                break
    
    return param_catalog, effect_types

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--aaf', default='tests/fixtures/aaf/candidate.aaf')
    parser.add_argument('--mode', choices=['inventory', 'values', 'compare'], default='inventory')
    args = parser.parse_args()
    
    if args.mode == 'inventory':
        catalog, types = inventory_all_parameters(args.aaf)
        
        print("=== EFFECT PARAMETER INVENTORY ===")
        print(f"Total unique parameters: {len(catalog)}")
        print(f"Effect type distribution: {dict(types)}")
        
        for param_name, data in sorted(catalog.items()):
            print(f"\n{param_name}:")
            print(f"  Usage: {data['count']} occurrences")
            print(f"  Types: {', '.join(data['types'])}")
            if len(data['values']) <= 3:
                print(f"  Values: {data['values']}")
            else:
                print(f"  Sample values: {data['values'][:3]}...")
