from pathlib import Path
import re


IMAGE_PATTERN = re.compile(
    r"ghcr\.io/zokhidkhanjarov/credit-scoring-mlops-agent:sha-[0-9a-f]{40}"
)


def _image_references(path: str) -> list[str]:
    content = (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
    return re.findall(r"image:\s*(\S+)", content)


def test_ai_agent_deployment_uses_immutable_sha_image():
    images = _image_references("k8s/agents/ai-agent-deployment.yaml")
    assert images
    assert all(IMAGE_PATTERN.fullmatch(image) for image in images if "credit-scoring-mlops-agent" in image)


def test_reconciliation_worker_uses_immutable_sha_image():
    images = _image_references("k8s/agents/ai-reconciliation-worker.yaml")
    agent_images = [image for image in images if "credit-scoring-mlops-agent" in image]
    assert agent_images
    assert all(IMAGE_PATTERN.fullmatch(image) for image in agent_images)
    assert "latest" not in agent_images


def test_agent_and_worker_share_the_same_immutable_image():
    agent_images = _image_references("k8s/agents/ai-agent-deployment.yaml")
    worker_images = _image_references("k8s/agents/ai-reconciliation-worker.yaml")

    agent_refs = [image for image in agent_images if "credit-scoring-mlops-agent" in image]
    worker_refs = [image for image in worker_images if "credit-scoring-mlops-agent" in image]

    assert agent_refs
    assert worker_refs
    assert agent_refs == worker_refs


def test_image_workflow_publishes_full_commit_sha_tags():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "ai-agent-image.yml"
    ).read_text(encoding="utf-8")

    assert "type=sha,format=long" in workflow


def test_image_workflow_syncs_manifests_from_built_commit():
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "ai-agent-image.yml"
    ).read_text(encoding="utf-8")

    assert "github.sha" in workflow
    assert "Pin Kubernetes manifests to built image" in workflow
    assert "git push origin HEAD:main" in workflow
    assert "[skip ci]" in workflow
