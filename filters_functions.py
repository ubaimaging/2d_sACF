#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filtering and Analysis Utilities for Lung Histology Images
"""
import matplotlib.pyplot as plt
import numpy as np
import cv2
from scipy import ndimage
from sklearn.mixture import GaussianMixture as GMM
try:
    from skimage import morphology
except ImportError:
    import importlib
    skimage_morph = importlib.import_module('skimage.morphology')
    morphology = skimage_morph

def basic_filtering(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), sigmaX=9, sigmaY=9)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_OTSU)
    return thresh


def remove_spots(img, min_size=900):
    """Remove small white spots and fill black holes in binary image."""

    def remove_small_white_objects(binary_image, min_size=100):
        mask = (binary_image == 255).astype(bool)
        cleaned = morphology.remove_small_objects(mask, min_size=min_size)
        return (cleaned.astype(np.uint8)) * 255

    def fill_black_holes(binary_image):
        return (ndimage.binary_fill_holes(binary_image > 0)).astype(np.uint8) * 255

    max_val = img.max()
    _, thresh = cv2.threshold(img, max_val - 1, 255, cv2.THRESH_BINARY)

    cleaned = remove_small_white_objects(thresh, min_size=min_size)
    filled = fill_black_holes(cleaned)
    #
    # plt.imshow(thresh)
    # plt.show()

    return filled


def gray_clustering(img, k):
    """Apply Gaussian Mixture Model clustering to grayscale image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (11, 11), sigmaX=20, sigmaY=20)

    img_reshaped = blurred.reshape(-1, 1)
    gmm = GMM(n_components=k, covariance_type='tied', random_state=1).fit(img_reshaped)
    labels = gmm.predict(img_reshaped)

    centers = np.uint8(gmm.means_)
    clustered = centers[labels].reshape(gray.shape)

    return clustered, centers, blurred


def compute_quadrant_tissue_air_ratio(binary_image):
    """
    Compute the average tissue/air ratio across 4 image quadrants.
    Assumes: tissue=0, air=1 in binary image.
    """
    h, w = binary_image.shape
    mid_h, mid_w = h // 2, w // 2

    quadrants = [
        binary_image[:mid_h, :mid_w],
        binary_image[:mid_h, mid_w:],
        binary_image[mid_h:, :mid_w],
        binary_image[mid_h:, mid_w:]
    ]

    ratios = []
    for q in quadrants:
        tissue = np.sum(q == 0)
        air = np.sum(q == 1)
        ratio = tissue / air if air > 0 else np.inf
        ratios.append(ratio)

    return np.round(np.mean(ratios), 1), ratios


def area_ratio(img):
    """Compute tissue-to-air ratio from binary image (white = tissue)."""
    white_pixels = cv2.countNonZero(img)
    total_pixels = img.size
    ratio = total_pixels / white_pixels - 1
    print("Tissue/Air Ratio:", round(ratio, 1))
    return round(ratio, 1)
