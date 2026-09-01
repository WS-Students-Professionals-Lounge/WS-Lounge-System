try:
    import database_fixed
    print('✓ Import successful')
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()
