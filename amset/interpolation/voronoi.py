import logging
import sys
import time

import numpy as np
from multiprocessing import cpu_count

from joblib import Parallel, delayed
from scipy.spatial.qhull import Voronoi, ConvexHull
from sklearn.neighbors.ball_tree import BallTree
from tqdm import tqdm

from amset import amset_defaults
from amset.misc.constants import output_width
from amset.misc.log import log_time_taken
from pymatgen.core.lattice import Lattice
from pymatgen.util.coord import lattice_points_in_supercell

__author__ = "Alex Ganose"
__maintainer__ = "Alex Ganose"
__email__ = "aganose@lbl.gov"
__date__ = "June 21, 2019"

pdefaults = amset_defaults["performance"]
logger = logging.getLogger(__name__)


class PeriodicVoronoi(object):
    """

    Say no existing packages (scipy.qhull, tess, pyvoro) can handle 250,000+
    points in a reasonable amount of time with reasonable memory requirements.
    Note this class works because most of the points are on a regular grid so
    it is valid to calculate the Voronoi diagram in blocks.
    """

    def __init__(self,
                 reciprocal_lattice: Lattice,
                 original_points: np.ndarray,
                 original_dim: np.ndarray,
                 extra_points: np.ndarray,
                 nworkers: int = pdefaults["nworkers"]):
        """

        Args:
            original_points:
            nworkers:
        """
        self._nworkers = nworkers if nworkers != -1 else cpu_count()

        supercell_points = get_supercell_points(
            [2, 2, 2], original_points)

        # want points in cartesian space so we can define a regular spherical
        # cutoff even if reciprocal lattice is not cubic. If we used a
        # fractional cutoff, the cutoff regions would not be spherical
        cart_points = reciprocal_lattice.get_cartesian_coords(
            supercell_points)

        cart_extra_points = reciprocal_lattice.get_cartesian_coords(
            extra_points)

        # small cutoff is slighly larger than the max regular grid spacing
        # means at least 1 neighbour point will always be included in each
        # direction
        dim_lengths = np.dot(1 / original_dim, reciprocal_lattice.matrix)
        small_cutoff = np.max(dim_lengths) * 1.01
        big_cutoff = small_cutoff * 2

        # use BallTree for quickly evaluating which points are within cutoffs
        tree = BallTree(cart_points)

        # big cutoff points are those which surround the extra points within
        # the big cutoff (it does not include the extra points themselves)
        big_cutoff_points_idx = np.concatenate(
            tree.query_radius(cart_extra_points, big_cutoff), axis=0)

        # Voronoi points are those we actually calculate in the Voronoi diagram
        # e.g. the big points + extra points
        voronoi_points = supercell_points[big_cutoff_points_idx]
        self._voronoi_points = np.concatenate((
            voronoi_points, extra_points))

        # small points are the points in original_points for which we want to
        # calculate the Voronoi volumes. Note this does not include the
        # indices of the extra points. Outside the small cutoff, the weights
        # will just be the regular grid weight.
        small_cutoff_points_idx = np.concatenate(
            tree.query_radius(cart_extra_points, small_cutoff), axis=0)

        # get the indices of small_cutoff_points in voronoi_points
        small_in_voronoi_idx = _get_loc(
            big_cutoff_points_idx, small_cutoff_points_idx)

        # get the indices of the small cutoff points + extra points
        # in voronoi points that we want the volumes for. The extra points
        # were just added at the end of big_cutoff_points, so getting their
        # indices is simple
        self._volume_points_idx = np.concatenate(
            (small_in_voronoi_idx,
             np.arange(len(extra_points)) + len(big_cutoff_points_idx)))

        # get the indices of the small_cutoff_points (not including the extra
        # points) in the original mesh. this works because the supercell
        # points are in the same order as the original mesh, just repeated for
        # each cell in the supercell
        small_in_original_idx = (
                small_cutoff_points_idx % len(original_points))

        # get the indices of the small cutoff points + extra points in the
        # final volume array. Note that the final volume array has the same
        # order as original_mesh + extra_points
        self._volume_in_final_idx = np.concatenate(
            (small_in_original_idx,
             np.arange(len(extra_points)) + len(original_points)))

        # prepopulate the final volumes array. By default, each point has the
        # volume of the original mesh. Note: at this point, the extra points
        # will have zero volume. This will array will be updated by
        # compute_volumes
        self._final_volumes = np.full(
            len(original_points) + len(extra_points),
            1 / len(original_points))
        self._final_volumes[len(original_points):] = 0


    def compute_volumes(self):
        logger.info("Calculating k-point Voronoi diagram:")
        logger.debug("  ├── num k-points near extra points: {}".format(
            len(self._voronoi_points)))
        t0 = time.perf_counter()

        # after some testing it seems like sorting the points before calculating
        # the Voronoi diagram can speed things up by > 1000x when there are many
        # points
        sorted_idx = np.argsort(self._voronoi_points, axis=0)[:, 1]

        # add the QJ option to qhull, necessary to slightly jiggle the points
        voro = Voronoi(self._voronoi_points[sorted_idx],
                       qhull_options="Qbb Qc Qz QJ")

        # need to unsort regions to get correct points
        inv_sorted_idx = np.argsort(sorted_idx)
        regions = voro.point_region[inv_sorted_idx][self._volume_points_idx]
        indices = np.array(voro.regions)[regions]
        vertices = [voro.vertices[i] for i in indices]

        log_time_taken(t0)

        volumes = self._final_volumes.copy()
        volumes[self._volume_in_final_idx] = self._get_voronoi_volumes(
            indices, vertices)

        zero_vols = volumes == 0
        if any(zero_vols):
            logger.warning("{} volumes are zero".format(np.sum(zero_vols)))

        inf_vols: np.ndarray = volumes == np.inf
        if any(inf_vols):
            logger.warning("{} volumes are infinite".format(np.sum(inf_vols)))

        sum_volumes = volumes.sum()
        vol_diff = abs(sum_volumes - 1)
        if vol_diff > 0.01:
            logger.warning("Sum of weights does not equal 1 (diff = {:.1f})... "
                           "renormalising weights".format(vol_diff * 100))
            volumes = volumes / sum_volumes

        return volumes

    def _get_voronoi_volumes(self, indices, vertices) -> np.ndarray:
        logger.info("Calculating k-point weights:")

        voronoi_info = tqdm(
            list(zip(indices, vertices)),
            total=len(indices),
            ncols=output_width,
            desc="    ├── progress",
            file=sys.stdout,
            bar_format='{l_bar}{bar}| {elapsed}<{remaining}{postfix}')

        t0 = time.perf_counter()
        volumes = Parallel(n_jobs=self._nworkers, prefer="processes")(
            delayed(_get_volume)(idx, verts) for idx, verts in voronoi_info)
        log_time_taken(t0)
        return np.array(volumes)



def _get_volume(indices, vertices):
    if -1 in indices:
        # some regions can be open
        return np.inf

    else:
        return ConvexHull(vertices).volume


def _get_loc(x, y):
    """
    Based on https://stackoverflow.com/questions/8251541

    Args:
        x:
        y:

    Returns:

    """
    # len(x) > len(y)
    index = np.argsort(x)
    sorted_x = x[index]
    sorted_index = np.searchsorted(sorted_x, y)
    yindex = np.take(index, sorted_index, mode="clip")
    mask = x[yindex] == y
    return yindex[mask]


def get_supercell_points(supercell_dim, points,
                         replicate_backwards=True):
    scale_matrix = np.array(supercell_dim, np.int16)
    if scale_matrix.shape != (3, 3):
        scale_matrix = np.array(scale_matrix * np.eye(3), np.int16)

    f_lat = lattice_points_in_supercell(scale_matrix)

    # get a list of supercell images, e.g. [[1, 0, 0], [2, 0, 0]]
    images = np.dot(f_lat, scale_matrix)

    if replicate_backwards:
        images = np.unique(np.concatenate((images, -images)), axis=0)

    repeated_points = np.tile(points, (len(images), 1))
    repeated_images = np.repeat(images, len(points), axis=0)

    return repeated_images + repeated_points

