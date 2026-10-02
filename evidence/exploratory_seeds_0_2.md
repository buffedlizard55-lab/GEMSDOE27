# Exploratory prototype (seeds 0-2) - not shipped, disclosed for transparency

Prototype: forward-cone (+-30 deg) nearest-other-component links from skeleton tips, dots every 3 px, evaluated
against hidden components (20 %/quadrant, seeds 0-2 x 4 folds), vs cones rotated +-90 deg.

| gap (px) | forward dots | forward TPw/FPw | control dots | control TPw/FPw | ratio |
|---|---|---|---|---|---|
| 3-6 | 1,511 | 0.0228 | 2,225 | 0.0373 | 0.61 |
| 6-10 | 3,275 | 0.0878 | 5,351 | 0.0861 | 1.02 |
| 10-20 | 9,469 | 0.1583 | 17,806 | 0.0773 | 2.05 |
| 20-40 | 19,039 | 0.1175 | 42,669 | 0.0487 | 2.42 |

Per fold (all gaps 3-40): NW 4.93x, NE_LidarGapHeavy 2.45x, SW 1.45x, SE 1.83x forward/control.
Pooled over all gap bins: forward 0.1175 vs controls 0.0592 / 0.0553.
