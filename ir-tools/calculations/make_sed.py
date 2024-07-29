from typing import Optional, List
from pathlib import Path

import astropy.units as u
import astropy.constants as const
import matplotlib.pyplot as plt
import numpy as np
from astropy.modeling.models import BlackBody
from astropy.table import Table
from ppdmod.data import set_data
from ppdmod.utils import load_data
from ppdmod.plot import plot_sed



def calc_blackbody(temperature: u.K, wavelengths: u.um,
                   weight: u.mas, scaling: Optional[str] = None) -> np.ndarray:
    """Calculate the blackbody radiation at a given temperature and wavelength."""
    spectral_density = BlackBody(temperature)(wavelengths).to(u.erg/u.cm**2/u.s/u.Hz/u.sr)
    flux = spectral_density * (weight**2).to(u.sr) * np.pi
    if scaling == "nu":
        flux = flux * (const.c / wavelengths.to(u.m)).to(u.Hz)
    else:
        flux.to(u.Jy)
    return flux


def plot_vizier_sed(target: str,
                    wavelength_range: Optional[List[float]] = None,
                    radius: Optional[float] = 1,
                    ax: Optional[plt.Axes] = None,
                    title: Optional[str] = None,
                    filters: Optional[List[str]] = None,
                    show_legend: Optional[bool] = False,
                    scaling: Optional[str] = None,
                    savefig: Optional[Path] = None) -> None:
    """Plots the target's photometry from Vizier.

    Parameters
    ----------
    target : str
    radius : float, optional
    """
    sed = Table.read(f"https://vizier.cds.unistra.fr/viz-bin/sed?-c={target}&-c.rs={radius}")

    if ax is None:
        fig = plt.figure(tight_layout=True)
        ax = plt.axes()
        ax.set_xlabel(r"$\lambda$ ($\mathrm{\mu}$m)")
        ax.set_ylabel("Flux (Jy)")
        ax.set_title(title)
    else:
        fig = None

    if filters is not None:
        for filter in filters:
            filtered_sed = sed[[filter_name.startswith(filter)
                                for filter_name in sed['sed_filter']]]

            for tabname in set(filtered_sed['_tabname']):
                subset = filtered_sed[filtered_sed['_tabname'] == tabname]
                frequency, flux = subset["sed_freq"], subset["sed_flux"]
                wavelength = (const.c/(frequency).to(u.Hz)).to(u.um)

                if wavelength_range is not None:
                    indices = np.where((wavelength > wavelength_range[0]) &
                                       (wavelength < wavelength_range[1]))[0]

                    if indices.size == 0:
                        continue

                    frequency = frequency[indices]
                    wavelength = wavelength[indices]
                    flux = flux[indices]

                if scaling == "nu":
                    flux = flux.to(u.erg/u.s/u.Hz/u.cm**2) * frequency.to(u.Hz)

                ax.scatter(wavelength, flux)
    else:
        for tabname in set(sed['_tabname']):
            subset = sed[sed['_tabname'] == tabname]
            frequency, flux = subset["sed_freq"], subset["sed_flux"]
            wavelength = (const.c/(frequency).to(u.Hz)).to(u.um)

            if wavelength_range is not None:
                indices = np.where((wavelength > wavelength_range[0]) &
                                   (wavelength < wavelength_range[1]))[0]

                if indices.size == 0:
                    continue

                frequency = frequency[indices]
                wavelength = wavelength[indices]
                flux = flux[indices]

            if scaling == "nu":
                flux = flux.to(u.erg/u.s/u.Hz/u.cm**2) * frequency.to(u.Hz)

            ax.scatter(wavelength, flux)

    if show_legend:
        ax.legend()

    if savefig is not None:
        plt.savefig(savefig, format=Path(savefig).suffix[1:], dpi=300)

    if fig is not None:
        plt.close()


if __name__ == "__main__":
    wavelength_range, scaling = [0, 15], "nu"
    wavelengths = np.linspace(wavelength_range[0], wavelength_range[1], 1000) * u.um
    wavelengths_dict = {"hband": [1.6]*u.um, "kband": [2.25]*u.um,
                        "lband": [3.2]*u.um, "mband": [4.7]*u.um,
                        "nband": [8., 9., 10., 11.3, 12.5]*u.um}

    fits_files = list((Path("/Users/scheuck/Data/fitting_data") / "hd142527").glob("*fits"))
    wavelength = np.concatenate((wavelengths_dict["lband"], wavelengths_dict["mband"], wavelengths_dict["nband"]))
    data = set_data(fits_files, wavelengths=wavelength, fit_data=["flux", "vis"])

    fig, ax = plt.figure(tight_layout=True), plt.axes()
    plot_sed(wavelength_range * u.um, scaling="nu", no_model=True, ax=ax)
    wl_flux, star_flux = load_data(Path("/Users/scheuck/Data/flux_data")  / "hd142527" / "HD142527_stellar_model.txt")

    temps, weights, bbs = [2000, 1500, 800], [0.38, 1, 1.7], []
    for temp, weight in zip(temps, weights):
        bb_flux = calc_blackbody(temperature=temp * u.K, wavelengths=wavelengths,
                                 weight=weight * u.mas, scaling=scaling)
        ax.plot(wavelengths, bb_flux, label=f"{temp} K")
        bbs.append(bb_flux)

    star_flux_nu = (star_flux * u.Jy).to(u.erg/u.s/u.Hz/u.cm**2) * (const.c / (wl_flux * u.um)).to(u.Hz)
    ax.plot(wl_flux, star_flux_nu, label="Star")

    bbs = np.sum([np.interp(wl_flux * u.um, wavelengths, bb) for bb in bbs], axis=0) * u.erg/u.s/u.cm**2
    combined_flux = bbs + star_flux_nu
    ax.plot(wl_flux, combined_flux, label="Combined")

    plot_vizier_sed("HD142527", wavelength_range * u.um, ax=ax,
                    filters=["2MASS", "WISE", "IRAS"], scaling=scaling)

    ax.set_xlabel(r"$\lambda$ ($\mathrm{\mu}$m)")
    ax.set_ylabel(r"$F_\nu\nu$ (erg s$^{-1}$ cm$^{-2}$)")
    plt.legend()
    plt.savefig("hd142527_sed.pdf", format="pdf", dpi=300)
