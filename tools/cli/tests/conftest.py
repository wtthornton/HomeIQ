from pathlib import Path
import sys


def _drop_foreign_src_modules(cli_src: Path) -> None:
    to_delete = []
    for name, module in list(sys.modules.items()):
        if not name.startswith("src"):
            continue
        module_file = getattr(module, "__file__", "")
        if not module_file:
            to_delete.append(name)
            continue
        module_path = Path(module_file).resolve()
        if not module_path.is_relative_to(cli_src):
            to_delete.append(name)
    for name in to_delete:
        sys.modules.pop(name, None)


def _add_cli_package():
    cli_dir = Path(__file__).resolve().parents[1]
    cli_src = cli_dir / "src"
    _drop_foreign_src_modules(cli_src)
    resolved = str(cli_dir)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


_add_cli_package()

