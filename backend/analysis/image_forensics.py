from pathlib import Path

from concurrent.futures import ThreadPoolExecutor

from backend.analysis.ela import generate_ela, calculate_ela_score
from backend.analysis.edge_detection import analyze_edges
from backend.analysis.wavelet_analysis import analyze_wavelet
from backend.utils.artifact_paths import artifact_path


def analyze_image(
    image_path: str,
    analysis_dir: str,
    save_artifacts: bool = True,
    evidence_id: str | None = None,
):
    image_path = Path(image_path)
    analysis_dir = Path(analysis_dir)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    analysis_dir.mkdir(parents=True, exist_ok=True)

    ela_path = artifact_path(analysis_dir, "ela")
    edge_path = artifact_path(analysis_dir, "edges")
    wavelet_path = artifact_path(analysis_dir, "wavelet")

    img_str = str(image_path)

    with ThreadPoolExecutor(max_workers=3) as executor:
        if save_artifacts:
            future_ela = executor.submit(generate_ela, img_str, str(ela_path))
            future_edge = executor.submit(_generate_edges_viz, img_str, str(edge_path))
            future_wavelet = executor.submit(_generate_wavelet_viz, img_str, str(wavelet_path))
        else:
            import os
            import tempfile
            tmp = tempfile.mkdtemp(dir=str(analysis_dir))
            future_ela = executor.submit(generate_ela, img_str, os.path.join(tmp, "ela.jpg"))
            future_edge = executor.submit(analyze_edges, img_str, os.path.join(tmp, "edge.jpg"))
            future_wavelet = executor.submit(analyze_wavelet, img_str, os.path.join(tmp, "wave.jpg"))

        ela_image = future_ela.result()
        edge_result = future_edge.result()
        wavelet_result = future_wavelet.result()

        if not save_artifacts:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    ela_score = calculate_ela_score(ela_image)

    if not isinstance(edge_result, dict):
        edge_result = {}
    if not isinstance(wavelet_result, dict):
        wavelet_result = {}

    edge_density = float(edge_result.get("edge_density", 0.0))
    wavelet_score = float(wavelet_result.get("wavelet_score", 0.0))

    artifacts = {}
    if save_artifacts:
        artifacts = {
            "ela": str(ela_path.resolve()),
            "edges": str(edge_path.resolve()),
            "wavelet": str(wavelet_path.resolve()),
        }

    return {
        "signals": {
            "ela_score": round(float(ela_score), 4),
            "edge_density": round(edge_density, 4),
            "wavelet_score": round(wavelet_score, 4),
        },
        "artifacts": artifacts,
        "artifacts_pending": not save_artifacts,
    }


def _generate_edges_viz(image_path: str, output_path: str) -> dict:
    from backend.utils.artifact_visualization import load_bgr, render_edge_overlay
    import cv2
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp()) / "e.jpg"
    result = analyze_edges(image_path, str(tmp))
    original = load_bgr(image_path)
    edges = cv2.imread(str(tmp), cv2.IMREAD_GRAYSCALE)
    if original is not None and edges is not None:
        cv2.imwrite(output_path, render_edge_overlay(original, edges))
    else:
        cv2.imwrite(output_path, edges if edges is not None else original)
    return result


def _generate_wavelet_viz(image_path: str, output_path: str) -> dict:
    from backend.utils.artifact_visualization import load_bgr, render_wavelet_heatmap
    import cv2
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp()) / "w.jpg"
    result = analyze_wavelet(image_path, str(tmp))
    original = load_bgr(image_path)
    wmap = cv2.imread(str(tmp), cv2.IMREAD_GRAYSCALE)
    if original is not None and wmap is not None:
        cv2.imwrite(output_path, render_wavelet_heatmap(original, wmap))
    else:
        cv2.imwrite(output_path, wmap if wmap is not None else original)
    return result
