# FISH Join - Join FISH nuclei and spots information

This ImageJ module combines the output of nuclei segmentors (e.g. QuPath) and spot detectors (like RS-FISH). It runs both plugins, then creates a table that lists each spot and its matching nucleus. Matching nuclei and spots can also be shown visually.

## Installation

1. Locate your ImageJ dir
2. Put the FISH\_Join directory in the `plugins` directory of ImageJ
3. Put the fish\_join\_modules in the `jars/Lib` directory if ImageJ. Note: you may need to create the `Lib` directory under `jars`.
4. Restart ImageJ

## Usage

The following actions are provided:


- `Detect nuclei and dots`: Run segmentation and joining on all images matching the given glob pattern under the given directory, including sub directories.
- `Highlight nuclei`: Open an image with the requested nuclei marked using an overlay. The spots inside these nuclei can be put in the ROI.
- `Show results for all files`: Open the final results table that lists all nuclei and spots
