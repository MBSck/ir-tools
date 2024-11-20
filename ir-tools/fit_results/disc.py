import pickle
from pathlib import Path

import astropy.units as u
import numpy as np
from dynesty import DynamicNestedSampler
from matadrs.utils.plot import Plotter
from ppdmod.data import set_data
from ppdmod.fitting import (
    compute_interferometric_chi_sq,
    compute_observables,
    get_labels,
    get_theta,
    get_units,
)
from ppdmod.options import OPTIONS
from ppdmod.plot import (
    plot_chains,
    plot_component_mosaic,
    plot_components,
    plot_corner,
    plot_fit,
    plot_interferometric_observables,
    plot_intermediate_products,
    plot_overview,
)

from ..tables import best_fit_parameters

np.seterr(over="ignore", divide="ignore")

# plot_kwargs = dict(
#     legend_format="short",
#     error=True,
#     subplots=True,
#     margin=0.3,
#     legend_size="medium",
#     sharex=True,
#     share_legend=True,
#     save=True,
# )

# lband_data = list(fits_dir.glob("*HAW*"))
# plot_fits = Plotter(lband_data[:3], plot_name="lband_data.pdf", save_dir=plot_dir)
# plot_fits.add_uv(uv_extent=150).add_flux().add_vis(corr_flux=True).add_t3(
#     unwrap=False
# )
# plot_fits.plot(**plot_kwargs)
#
# plot_fits = Plotter(
#     lband_data[4:], plot_name="lband_data_continuation.pdf", save_dir=plot_dir
# )
# plot_fits.add_uv(uv_extent=150).add_flux().add_vis(corr_flux=True).add_t3(
#     unwrap=False
# )
# plot_fits.plot(**plot_kwargs)
#
# plot_fits = Plotter(
#     list(fits_dir.glob("*AQU*")), plot_name="nband_data.pdf", save_dir=plot_dir
# )
# plot_fits.add_uv(uv_extent=150).add_flux().add_vis(corr_flux=True).add_t3(
#     unwrap=True
# )
# plot_fits.plot(**plot_kwargs)


def ptform():
    pass


# TODO: Fix the chi square here to get correct fit values
if __name__ == "__main__":
    data_dir = Path().home() / "Data"
    path = data_dir / "model_results" / "disc_fits" / "2024-11-20"
    path /= "test_inner_outer_fixed_new_calc"
    plot_dir, assets_dir = path / "plots", path / "assets"
    plot_dir.mkdir(exist_ok=True, parents=True)
    assets_dir.mkdir(exist_ok=True, parents=True)

    fits_dir = data_dir / "fitting_data" / "hd142527"
    wavelengths = {
        "hband": [1.7] * u.um,
        "kband": [2.15] * u.um,
        "lband": np.linspace(3.1, 3.4, 6) * u.um,
        "mband": np.linspace(4.7, 4.9, 4) * u.um,
        "nband": np.linspace(8, 15, 35) * u.um,
    }

    OPTIONS.model.output = "non-normed"
    fits_files = list((fits_dir).glob("*fits"))

    dim = 1024
    wavelengths = np.concatenate(
        (
            wavelengths["hband"],
            wavelengths["kband"],
            wavelengths["lband"],
            wavelengths["mband"],
            wavelengths["nband"],
        )
    )
    data = set_data(
        fits_files,
        wavelengths=wavelengths,
        fit_data=["flux", "vis"],
        set_std_err=["mband"],
        weights=[1.0, 0.02094934],
    )
    uncertainties = np.load(path / "uncertainties.npy")
    with open(path / "components.pkl", "rb") as f:
        components = pickle.load(f)

    theta = get_theta(components)
    component_labels = [component.label for component in components]

    # TODO: Check why the chi_sq is different here from the value that it should have
    rchi_sqs = compute_interferometric_chi_sq(
        *compute_observables(components),
        ndim=np.array(theta).size,
        method="linear",
        reduced=True,
    )
    print(f"Total reduced chi sq: {rchi_sqs[0]:.2f}")
    print(f"Individual reduced chi_sqs: {np.round(rchi_sqs[1:], 2)}")

    labels = get_labels(components)
    units = get_units(components)
    sampler = DynamicNestedSampler.restore(path / "sampler.save")
    plot_corner(sampler, labels, units, savefig=plot_dir / "corner.pdf")
    # plot_chains(sampler, labels, units, savefig=plot_dir / "chains.pdf")

    plot_overview(savefig=plot_dir / "overview.pdf")
    best_fit_parameters(
        labels,
        units,
        theta,
        uncertainties,
        save_as_csv=True,
        savefig=assets_dir / "disc.csv",
    )
    best_fit_parameters(
        labels,
        units,
        theta,
        uncertainties,
        save_as_csv=False,
        savefig=assets_dir / "disc",
    )
    plot_fit(components=components, savefig=plot_dir / "disc.pdf")
    plot_components(
        components, dim, 0.1, 10, norm=0.2, zoom=8, savefig=plot_dir / "components.pdf"
    )
    plot_component_mosaic(
        components, dim, 0.1, norm=0.2, savefig=plot_dir / "models.pdf", zoom=8
    )
    plot_intermediate_products(
        dim, wavelengths, components, component_labels, save_dir=plot_dir
    )
    # plot_interferometric_observables([1, 13.5]*u.um, components,
    #                                  component_labels, save_dir=fit_plot_dir)