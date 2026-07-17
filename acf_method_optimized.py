# acf_method_optimizado.py

import os
import glob
import csv
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from tkinter import messagebox
from filters_functions import *
from fit_functions import *
from aux import *

from tkinter.filedialog import askopenfilename


# Constantes
n, m = 1024, 1024
cant = 100

# Rutas de salida
report_name = datetime.now().strftime(r'C:\PycharmProjects\2d_sACF\data\Resultados-%Y-%m-%d-%H-%M.csv')
means_data = datetime.now().strftime(r'C:\PycharmProjects\2d_sACF\data\means_data-%Y-%m-%d-%H-%M.csv')



def preprocessing_file(file_image, ind):
    import cv2
    image = cv2.imread(file_image)
    if image.shape != (1024, 1024, 3):
        if image.shape == (2048, 2448, 3):
            image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
        cx, cy = image.shape[0] // 2, image.shape[1] // 2
        image = image[cx - n // 2: cx + n // 2, cy - n // 2: cy + n // 2]
    image_filtered, centers, blurred = gray_clustering(image, 3)
    image_filtered = remove_spots(image_filtered, min_size=900)
    ratio = area_ratio(image_filtered)
    return image_filtered, os.path.basename(file_image), ratio


def calcule_2D_ACF(img, apply_window):
    if apply_window:
        hann = np.hanning(n)[:, None] * np.hanning(n)
        img = img * hann
        fft_img = np.fft.fft2(img, s=(2048, 2048))
        psd = np.abs(fft_img) ** 2
        acf = np.fft.ifft2(psd).real
        acf = np.fft.fftshift(acf)
        acf = acf[n - n // 2:n + n // 2, n - n // 2:n + n // 2]
        ACF = (acf - acf.min()) / (acf.max() - acf.min())
    else:
        fftn = np.fft.fft2(img)
        psd = np.abs(fftn) ** 2
        ACF = np.fft.ifft2(psd).real
        ACF = (ACF - ACF.min()) / (ACF.max() - ACF.min())
        ACF = np.fft.fftshift(ACF)

    labels, best_levels = apply_kmeans_clustering(ACF, n_clusters=5)
    return ACF, best_levels


def select_best_cluster(fwhm_value, tissue_air_ratio):

    if tissue_air_ratio <= 0.6: return 4
    if tissue_air_ratio >= 5.0: return 1
    if fwhm_value > n // 4:
        return 4 if tissue_air_ratio <= 1.0 else 3 if tissue_air_ratio <= 2.0 else 2
    if fwhm_value >= n // 8:
        return 4 if tissue_air_ratio < 0.9 else 3 if tissue_air_ratio <= 2.0 else 2
    if tissue_air_ratio > 2.5:
        return 1 if tissue_air_ratio > 4.0 else 2 if tissue_air_ratio > 3.0 or fwhm_value < n // 16 else 3
    return 2 if tissue_air_ratio >= 2.0 else 3 if tissue_air_ratio >= 1.0 or fwhm_value > n // 8 else 4 if n // 10 > fwhm_value else 3


def process_image(args):
    path, ind = args
    img_filtered, file, tissue_air_ratio = preprocessing_file(path, ind)
    apply_window = tissue_air_ratio > 5.0
    ACFm, levels = calcule_2D_ACF(img_filtered, apply_window)
    fwhm_val = compute_acf_metrics(ACFm)
    cluster = select_best_cluster(fwhm_val, tissue_air_ratio)
    level = levels[cluster]
    sx_i, sy_i, angle = fit_contours(ACFm, n, file, level)

    if sy_i / sx_i > 2 and (sy_i >= n or sx_i > n // 4) or sy_i / sx_i > 3.9 and sy_i > n // 4:
        sy_i = sx_i
    if sy_i / sx_i > 3.0 and sy_i < n // 4:
        sx_i = sy_i

    sxy = (sx_i + sy_i) / 2
    note = ["Highly Instilled", "Instilled", "Medium", "Control"][4 - cluster]

    # if response:
    #     with open(report_name, 'a', newline='') as f:
    #         csv.writer(f).writerow([file, round(sxy, 2), round(tissue_air_ratio, 2)])

    return (ind, file, note, sxy, tissue_air_ratio)


def mean_calcule_parallel(imgs, response):
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_image, [(img, i) for i, img in enumerate(imgs)]))

    # ✅ Ordenar por índice original
    results.sort(key=lambda x: x[0])

    if response:
        for ind, file, note, sxy, ratio in results:
            with open(report_name, 'a', newline='') as f:
                csv.writer(f).writerow([file, round(sxy, 2), round(ratio, 2)])

        for i in range(0, len(results), 10):
            chunk = results[i:i + 10]
            if chunk:
                mean_sxy = round(np.mean([x[3] for x in chunk]), 2)
                note = chunk[0][2]
                ratio = round(np.mean([x[4] for x in chunk]), 2)
                with open(means_data, 'a', newline='') as f:
                    csv.writer(f).writerow([note, mean_sxy, ratio, note, "NA"])

    return results


if __name__ == '__main__':
    from tkinter import messagebox

    response = messagebox.askyesno("Data file?", "Do you want to save the data?")
    if response:
        with open(means_data, 'w', newline='') as f:
            csv.writer(f).writerow(['group', 'sxy', 'tissue/air', 'note', 'std'])
        with open(report_name, 'w', newline='') as f:
            csv.writer(f).writerow(['Image', 'Average sx_sy', 'tissue/air'])

    start = time.time()

    images_control = sorted(glob.glob(r'C:\PycharmProjects\2d_sACF\DB_10_12_24\B6ND-10\*.tif'))
    images_inst = sorted(glob.glob(r'C:\PycharmProjects\2d_sACF\DB_10_12_24\B6ND-INST\*.tif'))
    imgs_hfd = sorted(glob.glob(r'C:\PycharmProjects\2d_sACF\DB_10_12_24\B6 HFD\*.tif'))
    imgs_hfd_inst = sorted(glob.glob(r'C:\PycharmProjects\2d_sACF\DB_10_12_24\B6 HFD INST\*.tif'))

    mean_calcule_parallel(images_control, response)
    mean_calcule_parallel(images_inst, response)
    mean_calcule_parallel(imgs_hfd, response)
    mean_calcule_parallel(imgs_hfd_inst, response)

    print(f"\n✅ Proceso terminado en {round(time.time() - start, 2)} segundos.")
