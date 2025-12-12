import ast

# Read models.py
with open('app/models/models.py', 'r') as f:
    content = f.read()

# Parse and find all class definitions
tree = ast.parse(content)
classes = []
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        classes.append((node.name, node.lineno))

print("Classes defined in models.py:")
class_names = [c[0] for c in classes]
for name, lineno in classes:
    count = class_names.count(name)
    if count > 1:
        print(f"  ❌ {name} at line {lineno}: DUPLICATE (found {count} times total)")
    else:
        print(f"  ✓ {name} at line {lineno}")
