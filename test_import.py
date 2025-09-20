#!/usr/bin/env python3
"""Test script to check superadmin blueprint import and route registration"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from routes.superadmin import superadmin_bp
    print('Superadmin blueprint imported successfully')
    print('Blueprint name:', superadmin_bp.name)

    # Check deferred functions (routes that will be registered)
    print('Deferred functions (routes to be registered):')
    for func in superadmin_bp.deferred_functions:
        print(f'  Function: {func.f.__name__}')
        if hasattr(func, 'rule'):
            print(f'    Rule: {func.rule}')

    # Try to create the app and check registered routes
    print('\nTrying to create app and check routes...')
    from app import create_app
    app = create_app()

    print('App created successfully')
    print('Superadmin routes in app.url_map:')
    for rule in app.url_map.iter_rules():
        if 'superadmin' in rule.rule:
            print(f'  {rule.rule} - {rule.methods}')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()