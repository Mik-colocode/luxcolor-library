from __future__ import annotations

from pathlib import Path

from app.models.templates import TreeNode


class FilesystemService:
    def ensure_tree(self, root: Path, nodes: list[TreeNode], dry_run: bool = False) -> list[str]:
        created: list[str] = []
        for node in nodes:
            created.extend(self._ensure_node(root, node, dry_run))
        return created

    def _ensure_node(self, root: Path, node: TreeNode, dry_run: bool) -> list[str]:
        target = root / node.name
        created: list[str] = []
        if not target.exists():
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
        for child in node.children:
            created.extend(self._ensure_node(target, child, dry_run))
        return created

    def resolve_path(self, production_root: Path, relative: str) -> Path:
        return production_root / relative
