import shutil
from pathlib import Path

import astropy.units as u
import numpy as np
from matadrs.utils.plot import Plotter
from astropy.table import QTable
from astropy.io import fits
from tqdm import tqdm
from uncertainties import unumpy


def delete_add_ins(file: Path) -> None:
    """Deletes the oi_flux and oi_vis extensions."""
    with fits.open(file, mode="update") as hdul:
        if "oi_vis" in hdul or "oi_flux" in hdul:
            del hdul["oi_vis"]
            del hdul["oi_flux"]


def calculate_vis(file: Path, flux_file: Path, **kwargs) -> None:
    """Calculates the correlated fluxes from the
    squared visibilities and a total flux.

    Also adds the total flux to the file.
    """
    delete_add_ins(file)
    if not (dir := file.parent / "vis").exists():
        dir.mkdir(parents=True)

    if not (bad_data_dir := file.parent / "bad_data").exists():
        bad_data_dir.mkdir(parents=True)

    with fits.open(file, mode="readonly") as hdul:
        wavelengths = hdul["oi_wavelength"].data["eff_wave"]
        vis = hdul["oi_vis2"].copy()
        vis_header = vis.header.copy()

    wl_flux, flux_data = np.load(flux_file)
    flux_data = np.interp(wavelengths * u.m.to(u.um), wl_flux, flux_data)

    vis_header["EXTNAME"] = "oi_vis".upper()
    vis_header["TTYPE5"] = "visamp".upper()
    vis_header["TTYPE6"] = "visamperr".upper()
    vis.name = "oi_vis".upper()
    vis.columns[4].name = "visamp".upper()
    vis.columns[5].name = "visamperr".upper()

    vis2 = unumpy.uarray(vis.data["visamp"], vis.data["visamperr"])
    vis_data = unumpy.sqrt(vis2)
    vis_value = unumpy.nominal_values(vis_data)
    vis_err = unumpy.std_devs(vis_data)

    vis.data["visamp"] = vis_value * flux_data * u.Jy
    vis.data["visamperr"] = vis_err * flux_data * u.Jy

    shutil.copy(file, (new_file := dir / f"{file.stem}_vis.fits"))
    with fits.open(new_file, mode="update") as hdul:
        if np.max(hdul["oi_vis2"].data["vis2data"] > 1)\
                or np.min(hdul["oi_vis2"].data["vis2data"] < 0):
            file.rename(bad_data_dir / file.name)
            new_file.unlink()
            return

        flux_header = vis_header.copy()
        flux_header["EXTNAME"] = "oi_flux".upper()
        flux = fits.BinTableHDU(
            QTable({"WAVELENGTH": [wavelengths * u.um],
                    "FLUXDATA": [flux_data * u.Jy],
                    "FLUXERR": [flux_data * 0.1 * u.Jy]}),
            header=flux_header)
        hdul.append(flux)
        hdul.append(vis)
        hdul.flush()

    if not (plot_dir := file.parent / "plots").exists():
        plot_dir.mkdir(parents=True)
    if not (new_plot_dir := new_file.parent / "plots").exists():
        new_plot_dir.mkdir(parents=True)

    # original_plot = Plotter(file, save_dir=plot_dir)
    # new_plot = Plotter(new_file, save_dir=new_plot_dir)
    # original_plot.add_uv().add_vis().add_vis2().add_t3().plot(**kwargs)
    # new_plot.add_uv().add_vis().add_vis2().add_t3().plot(**kwargs)


if __name__ == "__main__":
    directory = Path("/Users/scheuck/Data/reduced_data/hd142527/pionier")
    flux_file = Path("/Users/scheuck/Data/flux_data/hd142527/hd142527_sed_fit.npy")
    for index, fits_file in enumerate(tqdm(list(directory.glob("*.fits")))):
        calculate_vis(fits_file, flux_file, margin=0.3, error=True, save=True)
