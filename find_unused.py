import ast

def find_unused(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    imports = set()
    used_names = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.add(alias.asname or alias.name)
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
                
    unused_imports = imports - used_names
    print(f"Unused imports in {filepath}: {unused_imports}")

find_unused('/root/bot.py')
find_unused('/root/portfolio_backtester.py')
