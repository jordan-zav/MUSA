# Software development status

MUSA is a general-purpose multifractal and structural analysis application.
The working tree contains experimental development in addition to the published
release. Local changes are not a new release until they are reviewed and packaged.

## Retained generic capabilities

- Global and local multifractal spectra and operational fit diagnostics.
- Overlapping multiscale windows, conservative line-length partition and
  numerical checks for grid origin, boundaries and sampling support.
- Canonical and zeta-weighted estimates reported separately.
- Planar line topology, proximity relations, local directions and configurable
  descriptive categories; no project-specific geological favorability rule.
- Desktop interface, Python API, GIS export and styles.
- Synthetic examples and automated numerical tests.

## Data and interpretation

The repository does not distribute private project inputs, deliverables,
production metrics or project-specific geological rule tables. Those materials
are maintained separately. Results from private studies are not included as
software validation or public benchmarks.

Model configuration and numerical quality describe the computation. They do not
establish permeability, prospectivity or a probability of geological success.
Generic numerical improvements need independent verification with synthetic
controls or appropriately licensed public data.

## Before a future release

Review the local development changes, run the automated checks and build the
application from the reviewed source. Audit the resulting distribution for
unexpected data and temporary files. No publication or version change is
authorized solely by this working-tree organization.
