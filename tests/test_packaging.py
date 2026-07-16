import json
import zipfile
from pathlib import Path

from musa.packaging import package_run_output


def test_package_run_output_creates_zip_with_grouped_files(tmp_path):
    (tmp_path / "analysis_report.csv").write_text("q,dq\n2,1.5\n", encoding="utf-8")
    (tmp_path / "multifractal_mother_agg.csv").write_text("mother_ix,alpha_w\n0,1.2\n", encoding="utf-8")
    (tmp_path / "musa_mother_cells.gpkg").write_bytes(b"GPKG")
    (tmp_path / "mother_spatial_alpha_w_q2.png").write_bytes(b"PNG")

    result = package_run_output(
        tmp_path,
        run_name="MUSA_Test_Run",
        run_config={"qmin": -4, "qmax": 4},
        execution_log="run ok",
    )

    zip_path = Path(result["zip_path"])
    assert zip_path.is_file()
    assert result["run_name"] == "MUSA_Test_Run"

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        assert "MUSA_Test_Run/README.txt" in names
        assert "MUSA_Test_Run/metadata/run_config.json" in names
        assert "MUSA_Test_Run/logs/execution_log.txt" in names
        assert "MUSA_Test_Run/analysis/analysis_report.csv" in names
        assert "MUSA_Test_Run/mother_cells/multifractal_mother_agg.csv" in names
        assert "MUSA_Test_Run/gis/musa_mother_cells.gpkg" in names
        assert "MUSA_Test_Run/figures/mother_spatial_alpha_w_q2.png" in names
        cfg = json.loads(zf.read("MUSA_Test_Run/metadata/run_config.json").decode("utf-8"))
        assert cfg["qmin"] == -4
