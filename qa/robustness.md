# Robustness checks

Headline numbers re-computed (a) without papers that have more than 25 authors and (b) with arXiv-only preprints included.
‘FLIPS’ marks a result whose direction changes (e.g. ratio crosses 1, z-score crosses ±2); such findings are reported as fragile.

| metric                      |   baseline |   no >25-author papers |   with preprints | robustness   |
|:----------------------------|-----------:|-----------------------:|-----------------:|:-------------|
| papers                      |   8985.000 |               8943.000 |        10255.000 |              |
| IIIT-H NMI                  |      0.539 |                  0.539 |            0.515 |              |
| IIIT-H cross-unit share     |      0.704 |                  0.704 |            0.697 |              |
| IIIT-H cross-unit z         |    -13.112 |                -13.112 |          -14.343 |              |
| IIIT-H hidden-glue flagged  |      6.000 |                  6.000 |            5.000 |              |
| IIIT-H share at 0 after 3y  |      0.439 |                  0.439 |            0.421 |              |
| IIIT-H top10 citation share |      0.685 |                  0.682 |            0.685 |              |
| IIIT-H cites-us-not-collab  |     45.000 |                 45.000 |           45.000 |              |
| IIIT-D NMI                  |      0.345 |                  0.345 |            0.334 |              |
| IIIT-D cross-unit share     |      0.378 |                  0.380 |            0.387 |              |
| IIIT-D cross-unit z         |    -11.598 |                -10.650 |          -10.400 |              |
| IIIT-D hidden-glue flagged  |      1.000 |                  1.000 |            1.000 |              |
| IIIT-D share at 0 after 3y  |      0.646 |                  0.646 |            0.635 |              |
| IIIT-D top10 citation share |      0.662 |                  0.672 |            0.662 |              |
| IIIT-D cites-us-not-collab  |     57.000 |                 57.000 |           57.000 |              |
| F5 cross/within ratio       |      0.800 |                  0.800 |            0.727 |              |