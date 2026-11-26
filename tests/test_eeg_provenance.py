import importlib.util
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pytest

from eeg_phase2 import download_eeg_data


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


recorder = load_script("record_first_session", ROOT / "v4.0-closed-loop" / "record_first_session.py")
replayer = load_script("replay_session", ROOT / "v4.0-closed-loop" / "replay_session.py")
convergence = load_script("convergence_plot", ROOT / "eeg_phase2" / "convergence_plot.py")


class FakeRaw:
    def __init__(self, data):
        self._data = data
        self.info = {"sfreq": 160.0}
        self.ch_names = ["C3", "C4"]
        self.filter_args = None

    def filter(self, *, l_freq, h_freq):
        self.filter_args = (l_freq, h_freq)

    def get_data(self):
        return self._data


class FakeEEGBCI:
    def __init__(self, returned_paths):
        self.returned_paths = returned_paths
        self.arguments = None

    def load_data(self, *, subjects, runs, path):
        self.arguments = (subjects, runs, path)
        return self.returned_paths


def valid_provenance(data):
    return {
        "schema_version": 1,
        "source_type": "EEGBCI",
        "source_dataset": "EEGBCI (PhysioNet) via MNE",
        "source_file": "returned.edf",
        "synthetic": False,
        "preprocessing": {"filter_hz": [1.0, 45.0]},
        "array": {
            "shape": list(data.shape),
            "dtype": str(data.dtype),
            "unit": "V",
            "sha256": hashlib.sha256(np.ascontiguousarray(data).tobytes(order="C")).hexdigest(),
        },
        "sampling_frequency_hz": 160.0,
    }


def test_downloader_uses_returned_local_path_and_writes_sidecar(tmp_path):
    expected_path = tmp_path / "mne-cache" / "not-a-hardcoded-name.edf"
    data = np.arange(640, dtype=np.float64).reshape(2, 320)
    fake_raw = FakeRaw(data)
    read_paths = []
    fake_mne = SimpleNamespace(
        io=SimpleNamespace(read_raw_edf=lambda path, preload: (read_paths.append((path, preload)) or fake_raw))
    )
    fake_eegbci = FakeEEGBCI([str(expected_path)])
    output = tmp_path / "out" / "raw_eeg.npy"

    saved_data, saved_metadata = download_eeg_data.download_and_preprocess(
        output,
        tmp_path / "dataset-cache",
        mne_api=fake_mne,
        eegbci_api=fake_eegbci,
    )

    assert read_paths == [(str(expected_path.resolve()), True)]
    assert fake_eegbci.arguments == (1, [1], str((tmp_path / "dataset-cache").resolve()))
    assert fake_raw.filter_args == (1.0, 45.0)
    np.testing.assert_array_equal(np.load(saved_data, allow_pickle=False), data)
    provenance = json.loads(saved_metadata.read_text())
    assert provenance["source_type"] == "EEGBCI"
    assert provenance["synthetic"] is False
    assert provenance["source_file"] == expected_path.name
    assert provenance["array"]["shape"] == [2, 320]
    assert len(provenance["array"]["sha256"]) == 64


def test_missing_mne_fails_without_creating_fake_output(tmp_path, monkeypatch):
    output = tmp_path / "new" / "raw_eeg.npy"

    def missing_mne():
        raise RuntimeError("MNE-Python is required; no synthetic EEG is generated.")

    monkeypatch.setattr(download_eeg_data, "_load_mne_components", missing_mne)
    with pytest.raises(RuntimeError, match="no synthetic EEG"):
        download_eeg_data.download_and_preprocess(output, tmp_path / "cache")
    assert not output.exists()
    assert not output.parent.exists()
    assert not (tmp_path / "cache").exists()


def test_downloader_refuses_to_overwrite_existing_output(tmp_path):
    output = tmp_path / "raw_eeg.npy"
    output.write_bytes(b"preserve this")
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        download_eeg_data.download_and_preprocess(output)
    assert output.read_bytes() == b"preserve this"


def test_downloader_rolls_back_if_sidecar_cannot_be_published(tmp_path, monkeypatch):
    data = np.ones((2, 320), dtype=np.float64)
    fake_raw = FakeRaw(data)
    fake_mne = SimpleNamespace(io=SimpleNamespace(read_raw_edf=lambda path, preload: fake_raw))
    fake_eegbci = FakeEEGBCI([str(tmp_path / "source.edf")])
    output = tmp_path / "out" / "raw_eeg.npy"
    original_link = download_eeg_data.os.link
    calls = 0

    def fail_second_link(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated sidecar publication failure")
        return original_link(source, target)

    monkeypatch.setattr(download_eeg_data.os, "link", fail_second_link)
    with pytest.raises(OSError, match="simulated sidecar publication failure"):
        download_eeg_data.download_and_preprocess(
            output,
            tmp_path / "cache",
            mne_api=fake_mne,
            eegbci_api=fake_eegbci,
        )
    assert not output.exists()
    assert not download_eeg_data.provenance_path_for(output).exists()
    assert not list(output.parent.glob("*.tmp"))


def test_recorder_requires_eegbci_provenance_and_rejects_synthetic(tmp_path):
    source = tmp_path / "raw_eeg.npy"
    np.save(source, np.ones((2, 320)))
    with pytest.raises(ValueError, match="Missing provenance"):
        recorder.load_verified_eeg(source)

    metadata = valid_provenance(np.ones((2, 320)))
    metadata["synthetic"] = True
    recorder.provenance_path_for(source).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="synthetic EEG provenance"):
        recorder.load_verified_eeg(source)


def test_recorder_rejects_same_shape_array_that_does_not_match_checksum(tmp_path):
    source = tmp_path / "raw_eeg.npy"
    data = np.ones((2, 320), dtype=np.float64)
    np.save(source, data)
    recorder.provenance_path_for(source).write_text(json.dumps(valid_provenance(data)))
    np.save(source, data * 2)
    with pytest.raises(ValueError, match="SHA-256"):
        recorder.load_verified_eeg(source)


def test_recorder_requires_sampling_frequency_in_provenance(tmp_path):
    source = tmp_path / "raw_eeg.npy"
    data = np.ones((2, 320), dtype=np.float64)
    np.save(source, data)
    metadata = valid_provenance(data)
    metadata.pop("sampling_frequency_hz")
    recorder.provenance_path_for(source).write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="sampling_frequency_hz"):
        recorder.load_verified_eeg(source)


def test_new_session_labels_proxy_and_simulated_fields(tmp_path):
    data = np.vstack([np.tile([0.0, 1.0], 160), np.tile([1.0, 0.0], 160)])
    session = recorder.create_session(data, valid_provenance(data), seed=7)

    assert session["metadata"]["record_type"] == "offline_demo_simulation"
    assert session["metadata"]["eeg_feature"]["is_iit_phi"] is False
    assert session["frames"][0]["eeg_binary_symbol_count"] == 2.0
    assert "phi_eeg" not in session["frames"][0]
    assert "phi_pred_simulated" in session["frames"][0]
    saved = recorder.save_session(session, tmp_path / "new-session.json")
    original = saved.read_bytes()
    with pytest.raises(FileExistsError):
        recorder.save_session(session, saved)
    assert saved.read_bytes() == original


def test_save_session_write_failure_does_not_publish_partial_file(tmp_path, monkeypatch):
    output = tmp_path / "new-session.json"

    def fail_after_partial_write(value, stream, **kwargs):
        stream.write('{"partial":')
        raise OSError("simulated serialization write failure")

    monkeypatch.setattr(recorder.json, "dump", fail_after_partial_write)
    with pytest.raises(OSError, match="simulated serialization write failure"):
        recorder.save_session({"complete": True}, output)

    assert not output.exists()
    assert not list(tmp_path.glob(".new-session.json.*.tmp"))


def test_save_session_racing_destination_collision_is_no_clobber(tmp_path, monkeypatch):
    output = tmp_path / "new-session.json"
    competing_bytes = b"created by competing writer"
    original_dump = recorder.json.dump

    def create_competing_destination(value, stream, **kwargs):
        output.write_bytes(competing_bytes)
        original_dump(value, stream, **kwargs)

    monkeypatch.setattr(recorder.json, "dump", create_competing_destination)
    with pytest.raises(FileExistsError):
        recorder.save_session({"complete": True}, output)

    assert output.read_bytes() == competing_bytes
    assert not list(tmp_path.glob(".new-session.json.*.tmp"))


def test_legacy_replay_is_unverified_and_plot_is_no_clobber(tmp_path):
    legacy_path = ROOT / "v4.0-closed-loop" / "session_recording.json"
    metadata, frames = replayer.load_session(legacy_path)
    assert metadata["record_type"] == "legacy_unverified"
    assert len(frames) == 100

    plot = tmp_path / "preview.png"
    saved = replayer.generate_plot(metadata, frames, plot)
    original = saved.read_bytes()
    assert original.startswith(b"\x89PNG")
    with pytest.raises(FileExistsError):
        replayer.generate_plot(metadata, frames, plot)
    assert saved.read_bytes() == original


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("eeg_binary_symbol_count", "invalid text"),
        ("phi_diwt_simulated", float("nan")),
        ("cycle", "invalid text"),
        ("cycle", float("nan")),
    ],
)
def test_replay_rejects_invalid_frames_before_output(tmp_path, capsys, field, value):
    session_path = tmp_path / "session.json"
    plot_path = tmp_path / "not-created" / "plot.png"
    frame = {
        "cycle": 1,
        "eeg_binary_symbol_count": 2.0,
        "phi_pred_simulated": 3.0,
        "phi_diwt_simulated": 4.0,
    }
    frame[field] = value
    session_path.write_text(
        json.dumps({"metadata": {"record_type": "offline_demo_simulation"}, "frames": [frame]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="finite number"):
        replayer.replay(session_path, plot_path, show_delay=False)

    assert capsys.readouterr().out == ""
    assert not plot_path.exists()
    assert not plot_path.parent.exists()


def test_generate_plot_rejects_invalid_metrics_before_creating_parent(tmp_path):
    plot_path = tmp_path / "not-created" / "plot.png"
    frames = [{"cycle": 1, "phi_eeg": "invalid text", "phi_diwt": 2.0}]

    with pytest.raises(ValueError, match="finite number"):
        replayer.generate_plot({"record_type": "legacy_unverified"}, frames, plot_path)

    assert not plot_path.exists()
    assert not plot_path.parent.exists()


def test_synthetic_convergence_plot_uses_new_path_and_refuses_overwrite(tmp_path):
    plot = tmp_path / "synthetic.png"
    convergence.generate_convergence_plot(plot, seed=3)
    original = plot.read_bytes()
    assert original.startswith(b"\x89PNG")
    with pytest.raises(FileExistsError):
        convergence.generate_convergence_plot(plot, seed=3)
    assert plot.read_bytes() == original


def test_downloader_default_paths_are_in_user_cache_outside_repository():
    expected_cache = Path.home() / ".cache" / "diwt-v3.7-real-eeg"
    assert download_eeg_data.USER_CACHE_DIR == expected_cache
    assert download_eeg_data.DEFAULT_DATA_DIR == expected_cache / "eegbci"
    assert download_eeg_data.DEFAULT_OUTPUT == expected_cache / "raw_eeg.npy"
    assert not download_eeg_data.DEFAULT_DATA_DIR.resolve().is_relative_to(ROOT.resolve())
    assert not download_eeg_data.DEFAULT_OUTPUT.resolve().is_relative_to(ROOT.resolve())


def test_downloader_refuses_explicit_output_inside_repository_before_io(tmp_path):
    output = ROOT / "eeg_phase2" / ".pytest-forbidden-eeg-output" / "raw_eeg.npy"
    dataset = tmp_path / "dataset-cache"
    assert not output.parent.exists()

    with pytest.raises(ValueError, match="EEG output must be outside the repository"):
        download_eeg_data.download_and_preprocess(
            output,
            dataset,
            mne_api=object(),
            eegbci_api=object(),
        )

    assert not output.parent.exists()
    assert not dataset.exists()


def test_downloader_refuses_explicit_dataset_cache_inside_repository_before_io(tmp_path):
    output = tmp_path / "output" / "raw_eeg.npy"
    dataset = ROOT / "eeg_phase2" / ".pytest-forbidden-eeg-cache"
    assert not dataset.exists()

    with pytest.raises(ValueError, match="EEGBCI dataset cache must be outside the repository"):
        download_eeg_data.download_and_preprocess(
            output,
            dataset,
            mne_api=object(),
            eegbci_api=object(),
        )

    assert not dataset.exists()
    assert not output.parent.exists()
