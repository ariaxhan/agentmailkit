"""Quickstart gallery: renders a sample email set locally and, by construction, never sends."""
from __future__ import annotations

from pathlib import Path

from agentmailkit.quickstart import build_gallery, _preview_job
from agentmailkit.spec import Job, load_jobs


def _jobs(local_job):
    return {local_job.id: local_job}


def test_preview_job_forces_file_delivery_and_strips_send_side_effects():
    j = Job(id="x", prompt="p", delivery="gmail", model="anthropic:sonnet",
            dedup=True, post=["taper"])
    pj = _preview_job(j, model=None)
    assert pj.delivery == "file"   # a preview can never reach a real inbox
    assert pj.model == "echo"      # deterministic, no keys, no network
    assert pj.dedup is None        # show full content, not "already seen"
    assert pj.post == []           # no taper generation during a look-at-what-you-get demo


def test_gallery_renders_files_and_an_index(tmp_cfg, local_job, tmp_path):
    out = tmp_path / "gallery"
    receipt = build_gallery(tmp_cfg, _jobs(local_job), out_dir=out)
    assert receipt["sent"] is False
    assert not receipt["errors"]
    assert len(receipt["rendered"]) == 1
    index = Path(receipt["index"])
    assert index.is_file()
    body = index.read_text(encoding="utf-8")
    assert "Quickstart gallery" in body
    assert "Nothing was sent" in body
    card = receipt["rendered"][0]
    assert (out / card["file"]).is_file()


def test_gallery_never_uses_a_sending_backend(tmp_cfg, local_job, tmp_path):
    # Even if the source job asks for gmail, the gallery must render via file only.
    local_job.delivery = "gmail"
    receipt = build_gallery(tmp_cfg, _jobs(local_job), out_dir=tmp_path / "g2")
    assert not receipt["errors"]
    # No file was delivered anywhere but the gallery dir; nothing was sent.
    assert receipt["sent"] is False


def test_shipped_jobs_load(tmp_path):
    # The repo's own jobs/ dir must parse into real Job objects (guards a broken spec file).
    repo_jobs = Path(__file__).resolve().parents[1] / "jobs"
    jobs = load_jobs(repo_jobs)
    assert jobs, "no shipped jobs loaded"
    assert all(isinstance(j, Job) and j.id for j in jobs.values())
