"""
Tests for Mutual Funds SLM Training and GGUF Export Pipeline.
"""

import os
import json
import struct
import pytest
from pathlib import Path
from app.train_slm import (
    MutualFundDatasetPreparer,
    LoRATrainingEngine,
    GGUFQuantizerAndExporter,
)


class TestSLMTrainingAndExportPipeline:
    def test_sft_dataset_preparation(self, tmp_path):
        preparer = MutualFundDatasetPreparer(data_dir=tmp_path)
        out_file = preparer.build_sft_dataset()
        assert out_file.exists()

        with open(out_file, "r", encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]

        assert len(lines) >= 4
        # Verify statutory compliance and factor calculation in instruction dataset
        assert any("CAGR" in item["instruction"] for item in lines)
        assert any("guarantee" in item["instruction"].lower() for item in lines)
        assert any("Jensen's Alpha" in item["instruction"] for item in lines)

    def test_lora_training_generates_valid_safetensors_and_config(self, tmp_path):
        sft_path = tmp_path / "sft.jsonl"
        with open(sft_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"instruction": "test", "output": "response"}) + "\n")

        models_dir = tmp_path / "models"
        trainer = LoRATrainingEngine(output_dir=models_dir)
        res = trainer.train(sft_data_path=sft_path, epochs=2)

        assert res["status"] == "COMPLETED"
        assert res["final_loss"] < 2.5
        assert res["perplexity"] > 0

        # Check adapter_config.json
        config_file = models_dir / "adapter_config.json"
        assert config_file.exists()
        with open(config_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg["peft_type"] == "LORA"
        assert cfg["r"] == 16
        assert "q_proj" in cfg["target_modules"]

        # Check adapter_model.safetensors
        weights_file = models_dir / "adapter_model.safetensors"
        assert weights_file.exists()
        assert weights_file.stat().st_size > 0

        # Verify safetensors 8-byte uint64 header
        with open(weights_file, "rb") as f:
            header_size = struct.unpack("<Q", f.read(8))[0]
            header_json = f.read(header_size).decode("utf-8")
            meta = json.loads(header_json)
            assert any("lora_A" in k for k in meta.keys())
            assert any("lora_B" in k for k in meta.keys())

    def test_gguf_export_generates_valid_gguf_v3_container(self, tmp_path):
        models_dir = tmp_path / "models"
        exporter = GGUFQuantizerAndExporter(output_dir=models_dir)
        gguf_file = exporter.export_gguf("test_model_q4.gguf")

        assert gguf_file.exists()
        assert gguf_file.stat().st_size > 0

        # Verify GGUF magic bytes "GGUF" and version 3
        with open(gguf_file, "rb") as f:
            magic, version, tensor_count, kv_count = struct.unpack("<4sIII", f.read(16))
            assert magic == b"GGUF"
            assert version == 3
            assert tensor_count > 0
            assert kv_count == 6

        # Check manifest
        manifest_file = models_dir / "test_model_q4.gguf.manifest.json"
        assert manifest_file.exists()
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        assert manifest["quantization"] == "Q4_K_M"
        assert "llama.cpp" in manifest["compatibility"]
