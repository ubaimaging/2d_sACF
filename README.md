# 2d_sACF — 2D spatial autocorrelation analysis of lung alveolar septa

`2d_sACF` is a Python tool for **quantitative and observer-independent
assessment of alveolar septum thickening** in hematoxylin–eosin (H&E)
stained lung histology. It computes the two-dimensional spatial
autocorrelation function (2D-sACF) of a segmented tissue/air image, fits an
ellipse to the central correlation peak, and reports the characteristic
correlation length **σxy** (pixels) as a proxy for septum thickness.

The software was developed for, and used in, the study:

> *Quantitative and unbiased lung alveolar septum assessment in an LPS
> experimental mouse model using 2D-spatial correlation image analysis from
> hematoxylin and eosin slides.* BioTechniques (2026).
> [doi:10.1080/07366205.2026.2674608](https://doi.org/10.1080/07366205.2026.2674608)
> · Preprint: [doi:10.1101/2025.07.24.666548](https://doi.org/10.1101/2025.07.24.666548)

It ships with a PyQt5 graphical interface designed for biomedical users with
no programming experience, and can be packaged as a standalone Windows
executable.

---

## How it works

```
RGB H&E image ─► grayscale + Gaussian blur ─► GMM segmentation (k = 3)
              ─► binary tissue/air mask (spot removal + hole filling)
              ─► tissue/air ratio
              ─► 2D-sACF = IFFT(|FFT(mask)|²)   (Wiener–Khinchin)
              ─► K-means levels on the ACF ─► adaptive level selection
              ─► ellipse fit to the central ACF contour (OpenCV)
              ─► σxy = (σx + σy) / 2   + category label
```

| Step | Function | Module |
|---|---|---|
| Load, resize (2048×2448 → ½), centre-crop to 1024×1024 | `preprocessing_file` | `acf_method_optimized.py` |
| GMM gray-level segmentation | `gray_clustering` | `filters_functions.py` |
| Spot removal and hole filling | `remove_spots` | `filters_functions.py` |
| Tissue/air ratio | `area_ratio` | `filters_functions.py` |
| 2D-sACF via FFT (Hann window + zero padding when tissue/air > 5) | `calcule_2D_ACF` | `acf_method_optimized.py` |
| Peak FWHM of the ACF | `compute_acf_metrics` | `fit_functions.py` |
| ACF level selection | `apply_kmeans_clustering`, `select_best_cluster` | `fit_functions.py`, `acf_method_optimized.py` |
| Ellipse fit with validity checks | `fit_contours`, `is_valid_ellipse` | `fit_functions.py` |
| Full per-image pipeline | `process_image` | `acf_method_optimized.py` |
| Graphical interface | `EdemaAnalysisGUI` | `edema-analysis-gui-v3.py` |

**Output per image:** σxy (px), tissue/air ratio, ACF FWHM (px), selected
cluster (1–4) and category (`Highly Instilled`, `Instilled`, `Medium`,
`Control`). σxy is in pixels; convert to µm with your acquisition pixel size.

---

## Installation

### Option A — standalone executable (Windows, no Python needed)

Download the release `.zip`, extract it and run `AnalizadorEdema.exe`.
See [`GUIA_DE_USUARIO.md`](GUIA_DE_USUARIO.md) (Spanish) for a step-by-step
walkthrough.

### Option B — from source (Windows, macOS, Linux)

Requires Python ≥ 3.10.

```bash
git clone https://github.com/ubaimaging/2d_sACF.git
cd 2d_sACF

# conda
conda env create -f environment.yml
conda activate 2d_sacf

# or pip
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Usage

### Graphical interface

```bash
python edema-analysis-gui-v3.py
```

1. **Load** a folder of RGB `.tif` images (1024×1024, or 2048×2448 which is
   resized automatically).
2. **Calibrate**: preview the pre-processing (blur, segmentation, spot
   removal) on a few representative images.
3. **Process** the whole dataset (runs in a background thread).
4. **Results**: inspect the table, the ellipse fit for each image, and export
   per-image CSV and summary statistics.

### Python API

```python
from acf_method_optimized import preprocessing_file, calcule_2D_ACF, process_image

# Full pipeline on one image
idx, name, label, sxy, tissue_air = process_image(("path/to/image.tif", 0))
print(f"{name}: sigma_xy = {sxy:.1f} px, tissue/air = {tissue_air}, {label}")

# Individual steps
mask, name, ratio = preprocessing_file("path/to/image.tif", 0)
acf, levels = calcule_2D_ACF(mask, apply_window=ratio > 5.0)
```

Batch processing of several folders in parallel is available through
`mean_calcule_parallel(list_of_paths, save=True)`.

---

## Testing

```bash
pip install pytest
pytest -v
```

The test suite checks the mathematical properties of the 2D-sACF (peak
location, symmetry, normalisation, agreement with direct correlation), the
tissue/air ratio on masks of known composition, the FWHM estimate on
analytical Gaussians, and the end-to-end response of σxy to synthetic septal
networks of increasing wall thickness. Tests run automatically on every push
via GitHub Actions.

---

## Input requirements and limitations

- RGB brightfield H&E images; air spaces must be the brightest class.
- Analysis is performed on a 1024×1024 field. Larger images are
  centre-cropped; images smaller than 1024×1024 are not supported.
- σxy is reported in pixels; comparisons are only valid across images
  acquired with the same magnification and pixel size.
- Category labels were tuned on the C57BL/6 LPS model of the original study
  and should be re-validated for other models, stains or magnifications.

---

## Citation

If you use this software, please cite the BioTechniques article above and
the software itself (see [`CITATION.cff`](CITATION.cff); GitHub's
"Cite this repository" button generates BibTeX/APA).

## Contributing and support

Bug reports, questions and feature requests are welcome through
[GitHub Issues](https://github.com/ubaimaging/2d_sACF/issues). See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for how to contribute code.

## License

Distributed under the MIT License — see [`LICENSE`](LICENSE).

## Acknowledgements

Developed at the Advanced Bioimaging Unit, Institut Pasteur de Montevideo
and Universidad de la República, Uruguay.
