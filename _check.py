import ast, pathlib, sys
root = pathlib.Path('c:/Users/NazaraX/telegram-message-sender')
files = [
    'core/system_modes.py','core/resources.py','core/memory.py',
    'core/performance.py','core/error_manager.py','core/distribution.py',
    'core/adaptive_intelligence.py','core/wave_engine.py','core/campaign_controller.py',
    'gui/dashboard_tab.py','gui/analytics_tab.py','gui/campaign_tab.py','gui/main_window.py',
    'gui/messages_tab.py','gui/groups_tab.py','gui/accounts_tab.py','gui/log_tab.py',
    'gui/styles.py','main.py',
]
errors = []
for f in files:
    p = root / f
    try:
        ast.parse(p.read_text(encoding='utf-8'))
        print(f'OK  {f}')
    except SyntaxError as e:
        errors.append(f)
        print(f'FAIL {f}: {e}')
sys.exit(len(errors))
