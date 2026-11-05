# Ten SQL analyses and findings

Every query ran successfully on 5 November 2026 against `warehouse/nyc_mobility.duckdb`. Full SQL is under `sql/analytics/`; result CSVs are under `artifacts/analytics/`.

## 1. Monthly demand and fare trends

Business question: How did demand, base fare, distance, and duration change by month?

Trips ranged from 19.27 million in August 2025 to 22.12 million in May 2026. December 2025 produced 22.11 million trips, while February 2025 was the lowest complete month at 19.34 million. Average base fare peaked at $28.80 in June 2026. The data shows stable large-scale demand with seasonal peaks rather than a sustained decline.

## 2. Provider comparison

Business question: How do dispatching providers compare on volume and trip economics?

| Provider | Trips | Share | Avg base fare | Avg miles | Avg minutes |
|---|---:|---:|---:|---:|---:|
| Uber | 297,356,543 | 72.22% | $27.78 | 5.04 | 19.89 |
| Lyft | 114,382,943 | 27.78% | $25.43 | 4.75 | 19.37 |

Uber carried nearly three quarters of trips and had slightly longer and higher-fare trips.

## 3. Top pickup zones

Business question: Which TLC zones generate the most pickup demand?

LaGuardia Airport ranked first with 8,155,975 pickups, followed by JFK Airport with 6,796,906. Crown Heights North led non-airport zones with 5,374,211. Airport zones combine high volume with much longer average distances: 11.68 miles from LaGuardia and 17.92 from JFK.

## 4. Hourly demand

Business question: How does the daily demand curve differ between weekdays and weekends?

Weekday demand peaks at 08:00 with 40,013 average trips per day, showing the commute effect. Weekend demand peaks at 18:00 with 40,081 average trips per day and stays high into the evening. Weekend activity after midnight is also much higher than on weekdays.

## 5. Borough comparison

Business question: Where do trips originate, and how do trip economics differ?

| Pickup borough | Trips | Share | Avg miles | Avg base fare |
|---|---:|---:|---:|---:|
| Manhattan | 149,160,884 | 36.23% | 5.13 | $32.20 |
| Brooklyn | 111,412,292 | 27.06% | 4.09 | $22.69 |
| Queens | 90,422,674 | 21.96% | 6.18 | $29.05 |
| Bronx | 54,149,591 | 13.15% | 4.26 | $19.70 |
| Staten Island | 6,574,692 | 1.60% | 5.08 | $22.01 |

Manhattan leads volume and average base fare. Queens has the longest average distance, reflecting airport and cross-borough travel.

## 6. Popular routes

Business question: Which origin-destination pairs are most common when pickup and drop-off zones differ?

Bushwick North to Bushwick South led with 422,916 trips. Williamsburg North Side to Greenpoint followed with 417,719. The top airport corridor was LaGuardia Airport to Times Square/Theatre District with 367,675 trips and a $70.31 average base fare.

## 7. Borough movement

Business question: How much demand stays local or crosses borough boundaries?

Queens had the highest cross-borough share at 27.60%, followed by Manhattan at 25.18%. Staten Island had the highest same-zone share at 18.91% and the lowest cross-borough share at 10.71%. This indicates that service-area planning should distinguish dense local movement from bridge/tunnel and airport corridors.

## 8. Airport pickups

Business question: How do airport pickups compare on volume, distance, time, and fare?

| Airport zone | Pickups | Avg miles | Avg minutes | Avg base fare |
|---|---:|---:|---:|---:|
| LaGuardia | 8,155,975 | 11.68 | 34.79 | $60.69 |
| JFK | 6,796,906 | 17.92 | 45.62 | $75.92 |
| Newark zone | 24 | 7.09 | 24.68 | $45.15 |

JFK trips are longer and higher-fare, while LaGuardia has more pickup volume. The Newark pickup count is tiny because TLC zone 1 is outside the normal NYC pickup market; it should not be compared as a peer demand market.

## 9. Shared ride outcomes

Business question: How often is sharing requested and matched, and how do those trips differ?

Sharing was not requested for 97.62% of accepted trips. Requested-and-matched trips represented 1.37%, averaged 7.30 miles and 30.33 minutes, and had a $21.86 average base fare. Requested-but-not-matched trips represented 1.01%.

## 10. Distance and fare

Business question: How does trip length relate to volume, duration, and unit fare?

The 1-3 mile band dominated with 163,151,757 trips (39.62%). Average base fare per mile fell from $15.47 for sub-mile trips to $3.97 for trips over 20 miles, reflecting minimum charges and fixed pickup overhead. Trips over 20 miles averaged $115.66 base fare and 58.75 minutes.

## Main business conclusions

- Provider concentration is high: Uber accounts for 72.22% of accepted volume.
- Airports are the two largest pickup zones and drive long, high-fare trips.
- Weekday demand is commute-led; weekend demand shifts to evening and late-night hours.
- Manhattan leads pickup volume, while Queens trips travel farther on average.
- Short trips dominate trip count, but long trips carry much higher absolute fare.
