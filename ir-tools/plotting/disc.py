import pickle
from pathlib import Path

import astropy.units as u
import emcee
import numpy as np
from dynesty import DynamicNestedSampler
from ppdmod.data import set_data
from ppdmod.fitting import (
    compute_interferometric_chi_sq,
    get_labels,
    get_units,
)
from ppdmod.options import OPTIONS
from ppdmod.plot import (
    plot_components,
    plot_corner,
    plot_fit,
    plot_intermediate_products,
    plot_overview,
)
from ppdmod.utils import (
    windowed_linspace,
)

from ..tables import best_fit_parameters
from .oifits import plot_baselines

np.seterr(over="ignore", divide="ignore")


def ptform():
    pass


if __name__ == "__main__":
    data_dir = Path().home() / "Data"
    path = data_dir / "results" / "disc" / "2025-02-11"
    path /= "all_data"

    plot_dir, assets_dir = path / "plots", path / "assets"
    plot_dir.mkdir(exist_ok=True, parents=True)
    assets_dir.mkdir(exist_ok=True, parents=True)

    fits_dir = data_dir / "fitting" / "hd142527"
    wavelengths = {
        "hband": [1.7] * u.um,
        "kband": [2.15] * u.um,
        "lband": windowed_linspace(3.1, 3.8, OPTIONS.data.binning.lband.value) * u.um,
        "mband": windowed_linspace(4.65, 4.9, OPTIONS.data.binning.mband.value) * u.um,
        "nband": windowed_linspace(8.25, 12.75, OPTIONS.data.binning.nband.value)
        * u.um,
    }
    fits_files = list((fits_dir).glob("*fits"))

    OPTIONS.fit.fitter = "dynesty"
    OPTIONS.fit.condition = "sequential_radii"

    dim = 1024
    bands = ["hband", "kband", "lband", "mband", "nband"]
    wavelengths = np.concatenate([wavelengths[band] for band in bands])
    fit_data = ["flux", "vis", "t3"]
    data = set_data(
        fits_files,
        wavelengths=wavelengths,
        fit_data=fit_data,
    )
    if OPTIONS.fit.fitter == "emcee":
        sampler = emcee.backends.HDFBackend(path / "sampler.h5")
    else:
        sampler = DynamicNestedSampler.restore(path / "sampler.save")

    theta = np.load(path / "theta.npy")
    uncertainties = np.load(path / "uncertainties.npy")
    with open(path / "components.pkl", "rb") as f:
        components = OPTIONS.model.components = pickle.load(f)

    labels, units = get_labels(components), get_units(components)
    OPTIONS.fit.condition_indices = list(
        map(labels.index, (filter(lambda x: "rin" in x or "rout" in x, labels)))
    )
    component_labels = [component.label for component in components]

    # TODO: Check why the chi_sq is different here from the value that it should be?
    rchi_sqs = compute_interferometric_chi_sq(
        components,
        theta.size,
        method="linear",
        reduced=True,
    )
    print(f"Total reduced chi sq: {rchi_sqs[0]:.2f}")
    print(f"Individual reduced chi_sqs: {np.round(rchi_sqs[1:], 2)}")

    plot_format = "pdf"
    plot_corner(
        sampler,
        labels,
        units,
        savefig=(plot_dir / f"corner.{plot_format}"),
    )
    plot_overview(savefig=(plot_dir / f"overview.{plot_format}"))
    plot_overview(
        bands=["nband"],
        savefig=(plot_dir / f"overview_nband.{plot_format}"),
    )
    plot_overview(
        bands=["hband", "kband", "lband", "mband"],
        savefig=(plot_dir / f"overview_hlkmband.{plot_format}"),
    )
    plot_fit(components=components, savefig=(plot_dir / f"disc.{plot_format}"))
    plot_fit(
        components=components,
        bands=["nband"],
        savefig=(plot_dir / f"disc_nband.{plot_format}"),
    )
    plot_fit(
        components=components,
        bands=["hband", "kband", "lband", "mband"],
        ylims={"t3": [-15, 15]},
        savefig=(plot_dir / f"disc_hklmband.{plot_format}"),
    )
    zoom = 5
    plot_components(
        components,
        dim,
        0.1,
        3.5,
        norm=0.3,
        zoom=zoom,
        savefig=plot_dir / "image_lband.png",
    )
    plot_components(
        components,
        dim,
        0.1,
        10.5,
        norm=0.3,
        zoom=zoom,
        savefig=plot_dir / "image_nband.png",
    )
    best_fit_parameters(
        labels,
        units,
        theta,
        uncertainties,
        save_as_csv=True,
        savefig=assets_dir / "disc.csv",
        fit_method=OPTIONS.fit.fitter,
    )
    best_fit_parameters(
        labels,
        units,
        theta,
        uncertainties,
        save_as_csv=False,
        savefig=assets_dir / "disc",
        fit_method=OPTIONS.fit.fitter,
    )

    max_plots, number = 20, True
    # bands = ["hband", "kband", "lband", "nband"]
    bands = ["nband"]
    for band in bands:
        plot_baselines(
            fits_files,
            band,
            "vis",
            max_plots=max_plots,
            number=number,
            save_dir=plot_dir,
        )
        plot_baselines(
            fits_files,
            band,
            "visphi",
            max_plots=max_plots,
            number=number,
            save_dir=plot_dir,
        )
        # plot_baselines(
        #     fits_files,
        #     band,
        #     "t3",
        #     max_plots=max_plots,
        #     number=False,
        #     save_dir=plot_dir,
        # )
