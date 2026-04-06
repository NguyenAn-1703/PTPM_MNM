"""Management command to remap owner_session_id across persisted documents."""
import re
from typing import Dict, Optional

from django.core.management.base import BaseCommand, CommandError

from src.database import get_storage
from src.model_factory import get_embeddings


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _normalize_owner(raw_value: Optional[str], field_name: str) -> str:
    owner = str(raw_value or "").strip()
    if not owner:
        raise CommandError(f"{field_name} không được để trống")
    if len(owner) > 128:
        raise CommandError(f"{field_name} không được dài quá 128 ký tự")
    if not SESSION_ID_PATTERN.fullmatch(owner):
        raise CommandError(f"{field_name} chỉ được chứa chữ, số, dấu gạch ngang và gạch dưới")
    return owner


class Command(BaseCommand):
    help = "Remap owner_session_id from one owner to another (supports dry-run)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-owner",
            required=True,
            help="owner_session_id nguồn cần remap",
        )
        parser.add_argument(
            "--to-owner",
            required=True,
            help="owner_session_id đích sau remap",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ thống kê số bản ghi bị ảnh hưởng, không ghi dữ liệu",
        )
        parser.add_argument(
            "--skip-source",
            action="store_true",
            help="Bỏ qua remap source_documents.json",
        )
        parser.add_argument(
            "--skip-vector",
            action="store_true",
            help="Bỏ qua remap metadata trong FAISS docstore",
        )

    def handle(self, *args, **options):
        from_owner = _normalize_owner(options.get("from_owner"), "from_owner")
        to_owner = _normalize_owner(options.get("to_owner"), "to_owner")
        dry_run = bool(options.get("dry_run"))
        skip_source = bool(options.get("skip_source"))
        skip_vector = bool(options.get("skip_vector"))

        if from_owner == to_owner:
            raise CommandError("from_owner và to_owner phải khác nhau")
        if skip_source and skip_vector:
            raise CommandError("Không thể dùng đồng thời --skip-source và --skip-vector")

        storage = get_storage()

        source_result = {"scanned": 0, "updated": 0, "skipped": skip_source}
        vector_result = {"scanned": 0, "updated": 0, "skipped": skip_vector, "loaded": False}

        if not skip_source:
            source_result = self._remap_source_documents(
                storage=storage,
                from_owner=from_owner,
                to_owner=to_owner,
                dry_run=dry_run,
            )

        if not skip_vector:
            vector_result = self._remap_vector_documents(
                storage=storage,
                from_owner=from_owner,
                to_owner=to_owner,
                dry_run=dry_run,
            )

        total_updated = int(source_result.get("updated", 0)) + int(vector_result.get("updated", 0))

        mode_label = "DRY-RUN" if dry_run else "APPLY"
        self.stdout.write(self.style.NOTICE(f"[{mode_label}] remap owner_session_id: {from_owner} -> {to_owner}"))

        if source_result.get("skipped"):
            self.stdout.write("- source_documents: skipped")
        else:
            self.stdout.write(
                f"- source_documents: scanned={source_result['scanned']}, updated={source_result['updated']}"
            )

        if vector_result.get("skipped"):
            self.stdout.write("- faiss_docstore: skipped")
        elif not vector_result.get("loaded"):
            self.stdout.write("- faiss_docstore: not found")
        else:
            self.stdout.write(
                f"- faiss_docstore: scanned={vector_result['scanned']}, updated={vector_result['updated']}"
            )

        if total_updated > 0:
            if dry_run:
                self.stdout.write(self.style.WARNING("Dry-run hoàn tất. Không có thay đổi nào được ghi."))
            else:
                self.stdout.write(self.style.SUCCESS("Remap owner_session_id thành công."))
        else:
            self.stdout.write(self.style.WARNING("Không có bản ghi nào cần remap."))

    @staticmethod
    def _remap_source_documents(*, storage, from_owner: str, to_owner: str, dry_run: bool) -> Dict[str, int]:
        docs = storage.load_source_documents()
        if not docs:
            return {"scanned": 0, "updated": 0, "skipped": False}

        updated = 0
        for item in docs:
            metadata = item.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                item["metadata"] = metadata

            owner_session_id = str(metadata.get("owner_session_id", "")).strip()
            if owner_session_id != from_owner:
                continue

            metadata["owner_session_id"] = to_owner
            updated += 1

        if updated > 0 and not dry_run:
            storage.save_source_documents(docs)

        return {"scanned": len(docs), "updated": updated, "skipped": False}

    @staticmethod
    def _remap_vector_documents(*, storage, from_owner: str, to_owner: str, dry_run: bool) -> Dict[str, object]:
        try:
            vector_store = storage.load_vector_store(get_embeddings())
        except Exception as exc:
            raise CommandError(f"Không thể load FAISS vector store: {str(exc)}") from exc

        if vector_store is None:
            return {"scanned": 0, "updated": 0, "skipped": False, "loaded": False}

        updated = 0
        try:
            doc_values = list(vector_store.docstore._dict.values())
        except Exception as exc:
            raise CommandError(f"FAISS docstore không hợp lệ: {str(exc)}") from exc

        for doc in doc_values:
            metadata = doc.metadata or {}
            owner_session_id = str(metadata.get("owner_session_id", "")).strip()
            if owner_session_id != from_owner:
                continue

            metadata["owner_session_id"] = to_owner
            doc.metadata = metadata
            updated += 1

        if updated > 0 and not dry_run:
            storage.save_vector_store(vector_store)

        return {"scanned": len(doc_values), "updated": updated, "skipped": False, "loaded": True}
