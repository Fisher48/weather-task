#!/usr/bin/env python3
"""Получает текущую погоду городов из файла через wttr.in и печатает отчёт.

Только стандартная библиотека: urllib.request, json, dataclasses, collections.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

CITIES_FILE = Path(__file__).with_name("cities.txt")
API_URL_TEMPLATE = "https://wttr.in/{city}?format=j1"
REQUEST_TIMEOUT = 30
REQUEST_ATTEMPTS = 3
REQUEST_DELAY_SECONDS = 1.0


@dataclass
class WeatherData:
    city: str
    temperature_c: int
    country: str


def load_cities(path: Path) -> list[str]:
    """Читает список городов из файла в память, убирает пустые строки и дубликаты."""
    seen = set()
    cities = []
    for line in path.read_text(encoding="utf-8").splitlines():
        city = line.strip()
        if not city:
            continue
        key = city.casefold()
        if key in seen:
            continue
        seen.add(key)
        cities.append(city)
    return cities


def fetch_weather(city: str) -> WeatherData:
    """Запрашивает текущую погоду города и строит модель WeatherData."""
    url = API_URL_TEMPLATE.format(city=urllib.parse.quote(city))
    request = urllib.request.Request(url, headers={"User-Agent": "wttr-task/1.0"})
    last_error = None
    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return WeatherData(
                city=city,
                temperature_c=int(payload["current_condition"][0]["temp_C"]),
                country=payload["nearest_area"][0]["country"][0]["value"],
            )
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as error:
            last_error = error
            if attempt < REQUEST_ATTEMPTS:
                time.sleep(REQUEST_DELAY_SECONDS * attempt)
    raise RuntimeError(f"не удалось получить данные: {last_error}")


def collect_weather(cities: list[str]) -> list[WeatherData]:
    """Собирает данные по всем городам, пропуская те, по которым запрос не удался."""
    results = []
    for index, city in enumerate(cities):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)
        try:
            results.append(fetch_weather(city))
        except RuntimeError as error:
            print(f"Пропущен город {city}: {error}", file=sys.stderr)
    return results


def group_by_country(weather: list[WeatherData]) -> dict[str, list[WeatherData]]:
    grouped = defaultdict(list)
    for item in weather:
        grouped[item.country].append(item)
    return dict(grouped)


def print_cities(weather: list[WeatherData]) -> None:
    print("Погода по городам:")
    for item in weather:
        print(f"{item.city}, {item.country} {item.temperature_c:+d}°C")
    print()


def city_word(count: int) -> str:
    if count == 1:
        return "city"
    return "cities"


def print_countries(grouped: dict[str, list[WeatherData]]) -> None:
    print("Сводка по странам:")
    for country in sorted(grouped):
        temperatures = [item.temperature_c for item in grouped[country]]
        count = len(temperatures)
        average = round(sum(temperatures) / count)
        print(
            f"{country} - {count} {city_word(count)}, "
            f"avg: {average:+d}°C, "
            f"min: {min(temperatures):+d}°C, "
            f"max: {max(temperatures):+d}°C"
        )


def main() -> int:
    if not CITIES_FILE.exists():
        print(f"Файл со списком городов не найден: {CITIES_FILE}", file=sys.stderr)
        return 1

    cities = load_cities(CITIES_FILE)
    weather = collect_weather(cities)

    if not weather:
        print("Не удалось получить данные ни для одного города.", file=sys.stderr)
        return 1

    print_cities(weather)
    print_countries(group_by_country(weather))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())