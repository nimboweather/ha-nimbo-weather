# Nimbo Weather for Home Assistant

Minute-by-minute rain for the next 3 hours at your home, anywhere in the European radar coverage, from
[Nimbo Weather](https://nimboweather.com). Know when the rain starts and stops before you hang the washing, open the
skylight or start the mower.

## Entities

One device per place, with:

| Entity | Unit | Meaning |
|---|---|---|
| Precipitation now | mm/h | The newest radar at the place (or the forecast for now) |
| Rain starts in | min | 0 while it rains; unknown when no rain is expected in the next 3 hours |
| Rain stops in | min | While it rains: when it stops; unknown when dry or when the rain lasts past the forecast |
| Precipitation next hour | mm | Rain expected over the next 60 minutes |
| Forecast issued | timestamp | When the forecast was made |
| Rain within 30 minutes | on/off | On when it rains now or rain is expected within 30 minutes |

"Rain starts in" carries the forecast's sentence as the `summary` attribute ("Light rain starting in 25 min, for
about 40 min"). Rain means 0.2 mm/h or more. Where no radar sees the place, the values are unknown.

## Install

With [HACS](https://hacs.xyz): HACS > three dots > Custom repositories > add this repository's URL, type
"Integration". Install "Nimbo Weather" and restart Home Assistant.

By hand: copy `custom_components/nimbo_weather` into your `config/custom_components/` and restart.

## Set up

1. Get a free API key (no card) at [nimboweather.com](https://nimboweather.com/dashboard).
2. Settings > Devices & services > Add integration > Nimbo Weather.
3. Paste the key. The place defaults to your Home Assistant home; change it to add more places.

## Calls and limits

The integration updates every 5 minutes: one API call each time, about 8,700 calls a month per place. The Free plan
includes 20,000 calls a month, so two places fit. Change the interval under the integration's Configure button (5 to
60 minutes). If the month's calls run out, the integration waits and tries again later instead of insisting.

## Attribution

The entities carry "Rain forecast: Nimbo Weather" in their `attribution` attribute. On the Free plan, show it with a
link to nimboweather.com wherever you publish the data.

## Support

Questions: hello@nimboweather.com. MIT licence.
