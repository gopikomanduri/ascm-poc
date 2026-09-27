"""
Tests for ModelStorageRegistry remote storage offload and Git pointer manifests.
"""

import json
from pathlib import Path
import pytest
from app.model_storage_registry import ModelStorageRegistry


class TestModelStorageRegistry:
    def test_compute_sha256(self, tmp_path):
        test_file = tmp_path / "dummy_model.bin"
        test_file.write_bytes(b"GGUF_TEST_PAYLOAD_12345")
        
        sha = ModelStorageRegistry.compute_sha256(test_file)
        assert len(sha) == 64
        assert sha == "2615702f3b01054b2dfe3fe6ac7ceffad47dffeed26a9048ae21cea138aaf979"

    def test_generate_pointer_manifest_aws_s3(self, tmp_path):
        models_dir = tmp_path / "models"
        test_model = models_dir / "mutual_funds_slm.gguf"
        models_dir.mkdir(parents=True, exist_ok=True)
        test_model.write_bytes(b"GGUF_MODEL_SIMULATED_2GB")

        registry = ModelStorageRegistry(models_dir=models_dir)
        manifest = registry.generate_pointer_manifest(
            artifact_path=test_model,
            storage_provider="AWS_S3",
            remote_uri="s3://institutional-slm-vault/models/v1/mutual_funds_slm.gguf"
        )

        assert manifest["storage_provider"] == "AWS_S3"
        assert "aws s3 cp" in manifest["download_command"]
        assert manifest["git_tracking_policy"] == "POINTER_ONLY_BINARY_OFFLOADED"
        assert len(manifest["sha256"]) == 64

        pointer_file = models_dir / "model_registry_pointer.json"
        assert pointer_file.exists()
        with open(pointer_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["artifact_filename"] == "mutual_funds_slm.gguf"

    def test_generate_pointer_manifest_gdrive_and_gcs(self, tmp_path):
        models_dir = tmp_path / "models"
        test_model = models_dir / "mutual_funds_slm.safetensors"
        models_dir.mkdir(parents=True, exist_ok=True)
        test_model.write_bytes(b"SAFETENSORS_PAYLOAD")

        registry = ModelStorageRegistry(models_dir=models_dir)
        manifest_gcs = registry.generate_pointer_manifest(
            artifact_path=test_model,
            storage_provider="GOOGLE_CLOUD_STORAGE",
            remote_uri="gs://gcp-firm-models/mutual_funds_slm.safetensors"
        )
        assert manifest_gcs["storage_provider"] == "GOOGLE_CLOUD_STORAGE"
        assert "gcloud storage cp" in manifest_gcs["download_command"]

        manifest_gdrive = registry.generate_pointer_manifest(
            artifact_path=test_model,
            storage_provider="GOOGLE_DRIVE",
            remote_uri="https://drive.google.com/file/d/1A2B3C4D5E/view?usp=sharing"
        )
        assert manifest_gdrive["storage_provider"] == "GOOGLE_DRIVE"
        assert "Google Drive" in manifest_gdrive["download_command"]

    def test_upload_dry_run_command_generation(self, tmp_path):
        models_dir = tmp_path / "models"
        test_model = models_dir / "model.gguf"
        models_dir.mkdir(parents=True, exist_ok=True)
        test_model.write_bytes(b"DATA")

        registry = ModelStorageRegistry(models_dir=models_dir)
        res = registry.upload_to_storage(
            artifact_path=test_model,
            remote_uri="s3://my-bucket/weights/model.gguf",
            dry_run=True
        )
        assert res["status"] == "SIMULATED_READY"
        assert "aws s3 cp" in res["command"]
