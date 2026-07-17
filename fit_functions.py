import numpy as np
import cv2
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from skimage.measure import regionprops, label
from matplotlib.patches import Ellipse
from filters_functions import *
from typing import Tuple
import concurrent.futures


def rotate(vector: Tuple[float, float], theta: float) -> np.ndarray:
    """Rotate a 2D vector by theta degrees."""
    radians = np.radians(theta)
    rotation_matrix = np.array([[np.cos(radians), np.sin(radians)],
                                [-np.sin(radians), np.cos(radians)]])
    return rotation_matrix @ np.array(vector)


def compute_acf_metrics(acf_image: np.ndarray) -> float:
    """Compute FWHM from the 2D autocorrelation function."""
    peak_value = np.max(acf_image)
    half_max = peak_value / 2
    mask = acf_image >= half_max
    labeled_mask, num_features = label(mask, return_num=True)

    if num_features:
        props = regionprops(labeled_mask, acf_image)
        max_region = max(props, key=lambda r: r.area)
        fwhm = (max_region.major_axis_length + max_region.axis_minor_length) / 2
    else:
        fwhm = np.nan

    return round(fwhm, 2)


def apply_kmeans_clustering(acf: np.ndarray, n_clusters: int = 4) -> Tuple[np.ndarray, np.ndarray]:
    """Apply KMeans to cluster ACF values."""
    values = acf.flatten().reshape(-1, 1)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(values)
    labels = kmeans.labels_.reshape(acf.shape)
    centers = np.sort(kmeans.cluster_centers_.flatten())
    return labels, np.round(centers, 2)


def normalize_and_threshold(g: np.ndarray, thresh_level: float) -> Tuple[np.ndarray, np.ndarray]:
    """Normalize image and apply threshold."""
    norm = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    scaled_thresh = 255 * (thresh_level - g.min()) / (g.max() - g.min())
    _, binary = cv2.threshold(norm, scaled_thresh, 255, cv2.THRESH_BINARY)
    return norm, binary


def get_central_contour(binary: np.ndarray, center: Tuple[int, int]) -> np.ndarray:
    """Return the contour containing the image center or largest one."""
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.pointPolygonTest(cnt, center, False) >= 0:
            return cnt
    return max(contours, key=cv2.contourArea)


def is_valid_ellipse(cnt: np.ndarray, n: int) -> bool:
    """Evaluate if the contour is a valid ellipse candidate."""
    if len(cnt) < 5:
        return False

    (_, _), (height, width), _ = cv2.fitEllipse(cnt)
    if width > height:
        height, width = width, height

    if height > n // 2 and width > n // 4:
        return False

    aspect_ratio = height / width
    if aspect_ratio >= 4.0 or (aspect_ratio > 2.0 and height > n // 2):
        return False

    contour_area = cv2.contourArea(cnt)
    hull_area = cv2.contourArea(cv2.convexHull(cnt))
    if hull_area == 0 or contour_area / hull_area < 0.65:
        return False

    ellipse_area = np.pi * (height / 2) * (width / 2)
    if ellipse_area == 0:
        return False

    fit_error = abs(contour_area - ellipse_area) / ellipse_area
    return fit_error <= 0.30


def fit_contours(g: np.ndarray, n: int, file_name: str, thresh_level: float) -> Tuple[float, float, float]:
    """Fit an ellipse to the central contour of a thresholded ACF image."""
    center = (n // 2, n // 2)
    delta = 0.001 if thresh_level < 0.1 else 0.01

    while True:
        _, binary = normalize_and_threshold(g, thresh_level)
        cnt = get_central_contour(binary, center)
        if len(cnt) < 5:
            thresh_level += delta
            continue

        ellipse = cv2.fitEllipse(cnt)
        _, (w, h), _ = ellipse

        if is_valid_ellipse(cnt, n) and not (0.5 * h >= n / np.sqrt(2)) and h < n:
            break

        thresh_level += delta

    return round(w, 4), round(h, 4), ellipse[2]


def visualize_ellipse_fit(g: np.ndarray, n: int, thresh_level: float, file_name: str) -> None:
    """Visualize and draw the fitted ellipse and contour."""
    norm, binary = normalize_and_threshold(g, thresh_level)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnt = contours[0]
    (xc, yc), (w, h), angle = cv2.fitEllipse(cnt)

    fig, ax = plt.subplots()
    ax.imshow(g, interpolation="none", origin='upper',
              extent=(n // 2 - 200, n // 2 + 200, n // 2 - 200, n // 2 + 200), cmap='jet')
    ax.add_patch(Ellipse((n // 2, n // 2), width=w, height=h, angle=-angle,
                         edgecolor='magenta', facecolor='none', lw=2))

    c = ax.contour(g, levels=[thresh_level], origin='upper',
                   colors="w", extent=(n // 2 - 200, n // 2 + 200, n // 2 - 200, n // 2 + 200))
    plt.clabel(c, inline=True, colors='w', fontsize=8)

    xymaj = rotate((h / 2, 0), angle - 90)
    xymin = rotate((w / 2, 0), angle)
    ax.plot([n // 2, xymaj[0] + n // 2], [n // 2, xymaj[1] + n // 2], color='magenta')
    ax.plot([n // 2, xymin[0] + n // 2], [n // 2, xymin[1] + n // 2], color='magenta')

    ax.set_xlim(n // 2 - 100, n // 2 + 100)
    ax.set_ylim(n // 2 - 100, n // 2 + 100)
    ax.grid(color='k')
    plt.title(f'2D sACF cropped, contour @ g={round(thresh_level, 2)}, fit ellipse {file_name}')
    plt.tight_layout()
    plt.colorbar(ax.images[0], ax=ax, fraction=0.046, pad=0.04)
    plt.show()


def batch_compute_acf_metrics(acf_images: list) -> list:
    """Parallel computation of ACF metrics for a list of images."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(compute_acf_metrics, acf_images))
    return results
