import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eeg_phase2 import download_eeg_data


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


recorder = load_script(
    "record_first_session_for_targeted_tests",
    ROOT / "v4.0-closed-loop" / "record_first_session.py",
)
renderer = load_script(
    "render_eeg_baseline_for_targeted_tests",
    ROOT / "scripts" / "render_eeg_baseline.py",
)


def test_recorder_default_input_matches_downloader_default_output():
    assert recorder.DEFAULT_INPUT == download_eeg_data.DEFAULT_OUTPUT


def test_pdf_renderer_preserves_a_file_created_after_its_initial_check(tmp_path, monkeypatch):
    source = tmp_path / "note.md"
    source.write_text("# Minimal note\n", encoding="utf-8")
    destination = tmp_path / "preview.pdf"

    class RacingHTML:
        def __init__(self, *, string, base_url):
            self.string = string

        def write_pdf(self, target):
            destination.write_bytes(b"created concurrently")
            Path(target).write_bytes(b"rendered PDF")

    monkeypatch.setattr(renderer, "HTML", RacingHTML)

    with pytest.raises(FileExistsError):
        renderer.render(source, destination)

    assert destination.read_bytes() == b"created concurrently"
    assert not list(tmp_path.glob(".preview.pdf.*.tmp"))


def load_mapper_with_stub_torch(monkeypatch):
    fake_torch = types.ModuleType("torch")
    fake_torch.__path__ = []
    fake_nn = types.ModuleType("torch.nn")
    fake_nn.Module = object
    fake_torch.nn = fake_nn

    def fake_save(value, stream):
        stream.write(repr(value).encode("utf-8"))

    fake_torch.save = fake_save
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "torch.nn", fake_nn)
    return load_script(
        "neural_state_mapper_for_targeted_tests",
        ROOT / "eeg_phase2" / "neural_state_mapper.py",
    )


def test_mock_mapper_checkpoint_is_labeled_and_never_overwrites(tmp_path, monkeypatch):
    mapper = load_mapper_with_stub_torch(monkeypatch)

    assert mapper.DEFAULT_CHECKPOINT.name == "neural_state_mapper.mock.generated.pth"
    assert "synthetic" in mapper.train_mock_model.__doc__.lower()
    assert "real EEG" in mapper.train_mock_model.__doc__

    destination = tmp_path / "demo.pth"
    saved = mapper.save_mock_checkpoint({"demo": "weights"}, destination)
    original = saved.read_bytes()
    assert original == b"{'demo': 'weights'}"

    with pytest.raises(FileExistsError):
        mapper.save_mock_checkpoint({"demo": "different"}, destination)

    assert saved.read_bytes() == original
    assert not list(tmp_path.glob(".demo.pth.*.tmp"))
