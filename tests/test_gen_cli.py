import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

import sci_fakedata as sfd
from sci_fakedata.cli import demo_report, main


def test_seed_shapes_and_metadata():
    first = sfd.gen.normal(n=(8, 9), seed=42, conclusion="user-supplied")
    np.testing.assert_array_equal(first, sfd.gen.normal(n=(8, 9), seed=42))
    assert isinstance(first, np.ndarray) and first.synthetic
    assert first.conclusion == "user-supplied" and first[:2].conclusion == "user-supplied"
    assert sfd.gen.normal().shape == (1000,)
    np.testing.assert_array_equal(sfd.gen.normal(std=0, mean=3, n=10), np.full(10, 3.))


def test_white_errors_bias():
    errors = sfd.gen.error(n=100000, systematic=0.2, std=0.5, seed=121)
    assert errors.mean() == pytest.approx(0.2, abs=0.005)
    assert errors.std() == pytest.approx(0.5, abs=0.005)
    assert abs(np.corrcoef(errors[:-1], errors[1:])[0, 1]) < 0.02
    np.testing.assert_array_equal(sfd.gen.error(n=7, systematic=0.2, std=0), np.full(7, 0.2))


def test_red_noise():
    samples = sfd.gen.red_noise(n=20000, alpha=0.9, seed=71)
    assert np.corrcoef(samples[:-1], samples[1:])[0, 1] == pytest.approx(0.9, abs=0.03)
    assert samples.std() == pytest.approx(1, abs=0.08)


def test_uniform_empty_shape():
    samples = sfd.gen.uniform(n=(3, 7), low=2, high=4, seed=11)
    assert samples.shape == (3, 7) and ((samples >= 2) & (samples < 4)).all()
    assert sfd.gen.red_noise(n=0).shape == (0,)


@pytest.mark.parametrize("call", [lambda: sfd.gen.normal(n=-1), lambda: sfd.gen.normal(n=True),
                                 lambda: sfd.gen.normal(std=-1), lambda: sfd.gen.error(std=float("inf")),
                                 lambda: sfd.gen.red_noise(alpha=1), lambda: sfd.gen.uniform(low=3, high=2)])
def test_invalid_parameters(call):
    with pytest.raises(ValueError):
        call()


def test_public_data_demo():
    report = demo_report()
    assert len(report.shapes) == 6
    assert report.shapes["Fig.2b-1"] == (16, 2)
    assert report.shapes["Extended Data Fig.3f-3"] == (8, 2)
    findings = [f for f in report.findings if f.code == "sum_mismatch"]
    assert len(findings) == 1
    assert findings[0].metrics["actual"] == pytest.approx(100.3)
    assert any("nature.com" in n for n in report.notes)
    duplicate = next(f for f in report.findings if f.code == "duplicate_series")
    assert duplicate.metrics["finite_overlap"] == 8
    assert all("axis=0[1=1]" in label for label in duplicate.series)
    block = next(f for f in report.findings if f.code == "repeated_block")
    assert (block.metrics["block_start"], block.metrics["block_stop"]) == (1, 8)
    grid = next(f for f in report.findings if f.code == "coarse_difference_grid" and f.metrics["length"] == 16)
    assert grid.metrics["matches"] == 14
    assert grid.metrics["off_grid_indices"] == [5, 9]
    text = report.summary()
    assert "0.30657 + 99.99343 = 100.3" in text
    assert "原表行 / Excel row 4" in text
    assert "连续位置 / Consecutive positions: 2..8" in text
    assert text.count("=" * 78) >= 10
    assert "title_zh" in report.to_dict()["findings"][0]
    assert "RULE:" not in report.summary(max_findings=0)


def test_repeated_block_preserves_gaps():
    left = np.array([.3123, .7134, .2931, .6513, .1324, .8712, .4421, .9912])
    right = left.copy()
    right[0] += .25
    assert any(f.code == "repeated_block" for f in sfd.analyze.scan({"A": left, "B": right}).findings)
    right[4] = np.nan
    assert not any(f.code == "repeated_block" for f in sfd.analyze.scan({"A": left, "B": right}).findings)
    with pytest.raises(ValueError):
        sfd.analyze.scan(left, grid_fraction=1.1)


def test_cli_demo(tmp_path, capsys):
    text, data = tmp_path / "report.txt", tmp_path / "report.json"
    assert main(["demo", "-o", str(text), "--json", str(data)]) == 0
    assert text.exists()
    assert json.loads(data.read_text(encoding="utf-8"))["shapes"]["Fig.2b-1"] == [16, 2]
    assert "sum_mismatch" in capsys.readouterr().out


def test_cli_csv(tmp_path, capsys):
    path = tmp_path / "source.csv"
    path.write_text("A,B\n" + "\n".join(f"{i+.25},{i+.55}" for i in range(8)), encoding="utf-8")
    assert main(["analyze", str(path), "--show", "2"]) == 0
    assert "constant_offset" in capsys.readouterr().out


@pytest.mark.parametrize("override,expected", [(None, "gbk"), ("utf-8", "utf-8"), ("gb18030", "gb18030")])
def test_cli_terminal_encoding(tmp_path, override, expected):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "gbk"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    saved = tmp_path / "report.txt"
    command = [sys.executable, "-m", "sci_fakedata", "demo", "--show", "0", "-o", str(saved)]
    if override:
        command.extend(["--encoding", override])
    result = subprocess.run(command, env=env, capture_output=True, check=True)
    text = result.stdout.decode(expected)
    assert "数据体检单" in text and "总和翻车" in text
    assert "数据体检单" in saved.read_text(encoding="utf-8")


def test_cli_invalid_encoding(capsys):
    with pytest.raises(SystemExit) as error:
        main(["demo", "--encoding", "not-a-real-charset"])
    assert error.value.code == 2
    assert "unknown output encoding" in capsys.readouterr().err
