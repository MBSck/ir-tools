from pathlib import Path
from typing import List, Optional, Tuple

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.modeling.models import BlackBody


def create_sed(flux_files: List[Path],
               wl_range: Optional[List[u.um]] = [1, 14],
               ) -> Tuple[np.ndarray, np.ndarray]:
    """Create a SED from a list of flux files."""
    wl, flux = np.array([]), np.array([])
    for flux_file in flux_files:
        data = np.loadtxt(flux_dir / flux_file, unpack=True)
        wl, flux = np.concatenate((wl, data[0])), np.concatenate((flux, data[1]))
    ind = np.where((wl > wl_range[0]) & (wl < wl_range[1]))
    return wl[ind]*u.um, flux[ind]*u.Jy


def calc_blackbody(temperature: u.K, wavelengths: u.um, weight: u.mas) -> np.ndarray:
    """Calculate the blackbody radiation at a given temperature and wavelength."""
    scale = 1*u.erg/u.cm**2/u.s/u.AA/u.sr
    bb = BlackBody(temperature, scale=scale)(wavelengths).to(u.erg/u.cm**2/u.s/u.um/u.sr)
    return bb*(weight**2).to(u.sr)*np.pi


def plot_sed(flux_dir: Path) -> Tuple[np.ndarray, np.ndarray]:
    _, axarr = plt.subplots(2, 3, figsize=(15, 10))
    wl, flux = np.loadtxt(flux_dir / "HD+142666.sed.dat", unpack=True, comments="#", usecols=(1, 2))
    wl, flux = wl*u.AA, (flux*u.erg/u.s/u.cm**2/u.AA)
    scales = [u.erg/u.s/u.cm**2/u.AA, u.erg/u.s/u.cm**2/u.um, u.erg/u.s/u.cm**2/u.um]
    labels = [r"Angstrom", "Micron", "Micron"]

    for index_wl in range(2):
        for index, (scale, label) in enumerate(zip(scales, labels)):
            if index == 2:
                ranges = [1, 14]*u.um

                if index_wl == 0:
                    ranges = ranges.to(u.AA)

                ind = np.where((wl > ranges[0]) & (wl < ranges[1]))
                tmp_wl, tmp_flx = wl[ind], flux[ind]
            else:
                tmp_wl, tmp_flx = wl, flux

            if index != 0:
                tmp_wl = tmp_wl.to(u.um)

            tmp_flx = tmp_flx.to(scale)
            if index_wl == 1:
                tmp_flx *= tmp_wl

            axarr[index_wl, index].scatter(tmp_wl.value, tmp_flx.value)
            axarr[index_wl, index].set_yscale("log")
            if not index == 2:
                axarr[index_wl, index].set_xscale("log")
            
            if index_wl == 0:
                axarr[index_wl, index].set_ylabel(rf"$F_\lambda ({str(scale)})$")
            else:
                axarr[index_wl, index].set_ylabel(rf"$\lambda F_\lambda$ ({str(scale*u.um)})")

            axarr[index_wl, index].set_xlabel(rf"$\lambda$ ({label})")
                
    plt.savefig("sed_combined.pdf", format="pdf")
    plt.close()

    wl, flux = wl.to(u.um), flux.to(u.erg/u.s/u.cm**2/u.um)
    ind = np.where((wl > 1*u.um) & (wl < 6*u.um))
    wl, flux = wl[ind], flux[ind]
    flux *= wl

    # data = ["HD_142666_timmi2.txt", "10402847.ss"]
    # data = ["HD_142666_timmi2.txt"]
    data = ["HD142666_spitzer_psf.dat"]
    for dataset in data:
        wl_data, flux_data, *_ = np.loadtxt(flux_dir / dataset, unpack=True, comments="#", skiprows=1)
        wl_data, flux_data = wl_data*u.um, (flux_data*u.Jy).to(u.erg/u.s/u.cm**2/u.Hz)
        flux_data = flux_data.to(u.erg/u.s/u.cm**2, u.spectral_density(wl_data))
        wl, flux = np.concatenate((wl, wl_data)), np.concatenate((flux, flux_data))

    ind = np.argsort(wl)
    wl, flux = wl[ind], flux[ind]

    ind = np.where((wl > 1*u.um) & (wl < 14*u.um))
    return wl[ind], flux[ind]


if __name__ == "__main__":
    flux_dir = Path("/Users/scheuck/Data/flux_data/hd142666/")
    wl = np.linspace(300, 700, 3000)*u.nm
    bb = BlackBody(6500*u.K)(wl)
    # bb = calc_blackbody(6500*u.K, wl, 20*u.mas)
    plt.plot(wl.value, bb.value)
    plt.show()
    # wl, flux = plot_sed(flux_dir)
    # wl_star, flux_star, *_ = np.loadtxt(flux_dir / "HD142666_stellar_model.txt.gz",
    #                                     comments="#", unpack=True)
    # wl_star *= u.um
    # flux_star = (flux_star*u.Jy).to(u.erg/u.s/u.cm**2, u.spectral_density(wl_star))
    # flux_star = np.interp(wl, wl_star, flux_star)
    # flux -= flux_star

    # temps, ratios = [2100, 1500, 1100, 900, 500], [0.15, 0.7, 1.2, 2.3, 7]
    # wl_range = np.linspace(np.min(wl.value), np.max(wl.value), 300)
    # bbs = [calc_blackbody(temp*u.K, wl_range*u.um, ratio*u.mas) for temp, ratio in zip(temps, ratios)]

    # nband = np.where((wl > 8.0*u.um) & (wl < 14.0*u.um))
    # bb_combined = np.sum(bbs, axis=0)
    # bb_combined_interpn = np.interp(wl, wl_range*u.um, bb_combined)
    # inner_contribution = (bb_combined_interpn/flux.value)[nband]
    # np.save("flux_ratio_inner_disk_hd142666.npy", np.array([wl[nband], inner_contribution]))
    # print(inner_contribution*100)
    # plt.scatter(wl.value, flux.value, s=5, alpha=0.6, label="Data")

    # for index, bb in enumerate(bbs):
    #     plt.plot(wl_range, bb.value, label=f"{temps[index]} K")
    # plt.plot(wl_range, bb_combined, label=f"Combined")

    # plt.xlabel(r"Wavelength ($\mu$m)")
    # plt.ylabel(r"$\lambda F_{\lambda}$ (erg s$^{-1}$ cm$^{-2}$)")
    # plt.ylim([0, None])
    # plt.legend()

    # plt.savefig("lambda_flux_lambda.pdf", format="pdf")
    # plt.close()
