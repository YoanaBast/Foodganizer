import os
import ast
from pathlib import Path

BASE_DIR = Path(__file__).parent

EXCLUDE_DIRS = {'.venv', 'venv', '__pycache__', '.git', 'staticfiles', 'node_modules', 'migrations'}


def walk_files(extension):
    results = []
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file.endswith(extension):
                results.append(os.path.join(root, file))
    return results


# --- TEMPLATES ---
templates = walk_files('.html')
# exclude base template and partials (starting with _)
base_templates = [t for t in templates if os.path.basename(t) == 'base.html']
partial_templates = [t for t in templates if os.path.basename(t).startswith('_')]
error_templates = [t for t in templates if os.path.basename(t) in ['404.html', '500.html', '400.html', '403.html', '405.html', '429.html']]
counted_templates = [t for t in templates if t not in base_templates and t not in partial_templates]

print("=" * 60)
print("TEMPLATES")
print("=" * 60)
print(f"Total .html files:        {len(templates)}")
print(f"Base templates:           {len(base_templates)}")
print(f"Partial templates (_*):   {len(partial_templates)}")
print(f"Error pages:              {len(error_templates)}")
print(f"Counted templates:        {len(counted_templates)}  (target: 15+)")
print()
for t in sorted(counted_templates):
    rel = os.path.relpath(t, BASE_DIR)
    print(f"  {rel}")


# --- FORMS ---
def count_forms_in_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        forms = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ''
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if 'Form' in base_name or 'FormSet' in base_name:
                        forms.append(node.name)
                        break
        return forms
    except Exception:
        return []

print()
print("=" * 60)
print("FORMS")
print("=" * 60)
all_forms = []
for f in walk_files('.py'):
    if 'forms.py' in f:
        found = count_forms_in_file(f)
        if found:
            rel = os.path.relpath(f, BASE_DIR)
            print(f"  {rel}:")
            for form in found:
                print(f"    - {form}")
            all_forms.extend(found)
print(f"Total form classes:       {len(all_forms)}  (target: 7+)")


# --- MODELS ---
def count_models_in_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            source = f.read()
        tree = ast.parse(source)
        models = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ''
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if base_name == 'Model' or base_name == 'AbstractUser' or base_name == 'AbstractBaseUser':
                        models.append(node.name)
                        break
        return models
    except Exception:
        return []

print()
print("=" * 60)
print("MODELS")
print("=" * 60)
all_models = []
for f in walk_files('.py'):
    if 'models.py' in f:
        found = count_models_in_file(f)
        if found:
            rel = os.path.relpath(f, BASE_DIR)
            print(f"  {rel}:")
            for m in found:
                print(f"    - {m}")
            all_models.extend(found)
print(f"Total model classes:      {len(all_models)}  (target: 5+)")


# --- DJANGO APPS ---
apps = []
for root, dirs, files in os.walk(BASE_DIR):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    if 'apps.py' in files:
        apps.append(os.path.relpath(root, BASE_DIR))

print()
print("=" * 60)
print("DJANGO APPS")
print("=" * 60)
for app in sorted(apps):
    print(f"  {app}")
print(f"Total apps:               {len(apps)}  (target: 5+)")


# --- TESTS ---
test_files = [f for f in walk_files('.py') if os.path.basename(f).startswith('test')]
total_tests = 0
print()
print("=" * 60)
print("TESTS")
print("=" * 60)
for f in test_files:
    try:
        with open(f, encoding='utf-8') as fh:
            source = fh.read()
        tree = ast.parse(source)
        count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
        )
        rel = os.path.relpath(f, BASE_DIR)
        print(f"  {rel}: {count} tests")
        total_tests += count
    except Exception:
        pass
print(f"Total tests:              {total_tests}  (target: 15+)")


# --- CBVs vs FBVs ---
print()
print("=" * 60)
print("CBVs vs FBVs (rough count)")
print("=" * 60)
cbv_count = 0
fbv_count = 0
cbv_bases = {'View', 'ListView', 'DetailView', 'CreateView', 'UpdateView', 'DeleteView', 'TemplateView', 'FormView', 'APIView', 'ModelViewSet', 'GenericAPIView'}
for f in walk_files('.py'):
    if 'views' in f and f.endswith('.py'):
        try:
            with open(f, encoding='utf-8') as fh:
                source = fh.read()
            tree = ast.parse(source)
            rel = os.path.relpath(f, BASE_DIR)
            file_cbvs = []
            file_fbvs = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_name = base.id if isinstance(base, ast.Name) else (base.attr if isinstance(base, ast.Attribute) else '')
                        if any(b in base_name for b in cbv_bases):
                            file_cbvs.append(node.name)
                            cbv_count += 1
                            break
                if isinstance(node, ast.FunctionDef):
                    if node.args.args and node.args.args[0].arg == 'request':
                        file_fbvs.append(node.name)
                        fbv_count += 1

            if file_cbvs or file_fbvs:
                print(f"\n  {rel}")
                if file_cbvs:
                    print(f"    CBVs ({len(file_cbvs)}):")
                    for name in file_cbvs:
                        print(f"      - {name}")
                if file_fbvs:
                    print(f"    FBVs ({len(file_fbvs)}):")
                    for name in file_fbvs:
                        print(f"      - {name}")
        except Exception:
            pass

total_views = cbv_count + fbv_count
cbv_pct = round(cbv_count / total_views * 100) if total_views else 0
print(f"\nTotal CBVs: {cbv_count}, Total FBVs: {fbv_count}, CBV%: {cbv_pct}%  (target: ~90% CBV)")


print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Templates (excl. base):   {len(counted_templates)}/15+")
print(f"Forms:                    {len(all_forms)}/7+")
print(f"Models:                   {len(all_models)}/5+")
print(f"Apps:                     {len(apps)}/5+")
print(f"Tests:                    {total_tests}/15+")
print(f"CBV ratio:                {cbv_pct}%/90%+")