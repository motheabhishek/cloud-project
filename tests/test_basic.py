import glob, py_compile, yaml

def test_manifests_parse():
    files = glob.glob("k8s/*.yaml") + glob.glob("network/*.yaml")
    assert files
    for f in files:
        with open(f) as fh:
            list(yaml.safe_load_all(fh))

def test_python_compiles():
    for f in ["service/app.py", "training/train.py", "tools/score.py", "worker/clean.py"]:
        py_compile.compile(f, doraise=True)
