.. raw:: html

  <style type="text/css">
    div.body li.toctree-l1 {
        padding: 0.5em 0 0.2em 0 ;
        list-style-type: none;
        font-size: 150% ;
        }

    div.body li.toctree-l2 {
        font-size: 70% ;
        list-style-type: square;
        }

    div.body li.toctree-l3 {
        font-size: 85% ;
        list-style-type: circle;
        }

    div.bodywrapper blockquote {
	margin: 0 ;
    }

  </style>

.. title:: AMSET: ab initio scattering and transport

AMSET: *ab initio* scattering and transport
===========================================

Introduction
------------

Accurately calculating electronic transport properties from first-principles
is often highly computationally expensive and difficult to perform. AMSET is a
fast and easy-to-use package to model carrier transport in solid-state materials.
A primary aim of AMSET is to be **amenable to high-throughput screenings**.
Features of AMSET include:

- All inputs easily obtainable from first-principles calculations. The
  primary input for AMSET is an *ab initio* uniform band structure.
- Scattering rates approximated based on common materials properties
  such as phonon frequencies and dielectric constants.
- Transport properties calculated by solving the iterative Boltzmann transport
  equation.
- Heavily optimised code that can run on a personal laptop. High-performance
  computing clusters not necessary.

AMSET is built on top of state-of-the-art open-source libraries:
`BoltzTraP2 <http://boltztrap.org/>`_ for band structure interpolation,
`numpy <https://www.numpy.org/>`_ and
`scipy <https://scipy.org>`_ to enable high-performance matrix operations, and
`pymatgen <http://pymatgen.org>`_ for handling DFT calculation data.

*Note: Currently, AMSET is best integrated with VASP, however,
support for additional periodic DFT codes will be added in the future.*

Scattering Mechanisms
~~~~~~~~~~~~~~~~~~~~~

The scattering mechanisms currently implemented in AMSET are:

- Acoustic deformation potential scattering
- Ionized impurity scattering
- Polar optical phonon scattering
- Piezoelectric scattering

More information on the formalism for each scattering mechanism is available
in the `scattering section <scattering>`_ of the documentation.

User manual
--------------

 .. toctree::
    :maxdepth: 2

    installation.rst
    using.rst
    settings.rst
    scattering.rst
    theory.rst

.. toctree::
   :hidden:
   :maxdepth: 2

   changelog
   contributors
   references
   license
   Python API <modules>

What's new?
-----------

Track changes to AMSET through the :doc:`changelog`.

Contributing / Contact / Support
--------------------------------

Want to see something added or changed? Some ways to get involved are:

- Help us improve the documentation – tell us where you got stuck and improve
  the install process for everyone.
- Let us know if you'd like to see certain features.
- Point us to areas of the code that are difficult to understand or use.
- Contribute code. You can do this by forking
  `AMSET on Github <https://github.com/hackingmaterials/amset>`_ and submitting
  a pull request.

The list of contributors to AMSET can be found :doc:`here </contributors>`.
Read more about contributing code to AMSET :doc:`here </contributing>`.

API documentation
------------------

Autogenerated API documentation below:

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`



