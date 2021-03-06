import sys
from datetime import datetime
import statistics

import pandas
from scipy.stats import linregress

import src.point as point


def main():
    if len(sys.argv) not in (3, 4):
        exit("Invalid number of arguments. Input and output .csv files' names required, may be followed by cities csv")

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    data_frame = pandas.read_csv(input_file, usecols=["dt", "AverageTemperature", "City", "Latitude", "Longitude"])
    data_by_location = data_frame.groupby(by=["City", "Latitude", "Longitude"], as_index=False)
    data_by_location = data_by_location.apply(temperature_series_to_regression)
    data_by_location = data_by_location.reset_index()

    if len(sys.argv) == 4:
        cities_file = sys.argv[3]
        cities_data_frame = pandas.read_csv(cities_file, usecols=["AccentCity", "Latitude", "Longitude"],
                                            encoding="ISO-8859-1")
        cities_data_frame = cities_data_frame\
            .assign(acccity=lambda df: df['AccentCity'].str.lower())\
            .set_index('acccity')
        data_by_location = data_by_location.apply(fix_cities_location, axis=1, cities_data_frame=cities_data_frame)

    data_by_location = data_by_location.drop_duplicates(subset=["Latitude", "Longitude"])
    data_by_location.to_csv(output_file, header=True)

    points = point.load_from_csv(output_file)
    locations = [(p.longitude, p.latitude) for p in points]
    unique_locations = set(locations)

    print("Points: {}, Unique points: {}".format(len(locations), len(unique_locations)))

    median, mean = count_stats(data_by_location)
    print("Average regression: {}, median: {}".format(mean, median))


def temperature_series_to_regression(temperatures: pandas.Series):
    temperatures = temperatures.dropna()
    regression = linregress(temperatures["dt"].map(map_date), temperatures["AverageTemperature"])[0]
    print("{}: {}".format(list(temperatures["City"])[0], regression))
    return pandas.Series(regression, index=["Regression"])


def fix_cities_location(data_by_location, cities_data_frame):
    city = data_by_location['City'].lower()
    if city in cities_data_frame.index:
        results = cities_data_frame.loc[[city]]
        if results.shape[0] != 1:
            print("{}: {} results".format(data_by_location['City'], results.shape[0]))
            orig = point.Point(data_by_location['Latitude'], data_by_location['Longitude'])
            results = results\
                .assign(f=lambda r: [orig.dist(point.Point(lat, lon)) for lat, lon in zip(r.Latitude, r.Longitude)])\
                .sort_values('f')\
                .drop('f', axis=1)

            print("Changed location from {}, {} to {}, {}".format(
                data_by_location['Latitude'], data_by_location['Longitude'],
                results.iloc[0]['Latitude'], results.iloc[0]['Longitude']))

        data_by_location['Latitude'] = results.iloc[0]['Latitude']
        data_by_location['Longitude'] = results.iloc[0]['Longitude']
    else:
        print("{}: no results".format(data_by_location['City']))

    return data_by_location


def map_date(date_string):
    return datetime.strptime(date_string, "%Y-%M-%d").year


def count_stats(data):
    median = statistics.median(data['Regression'])
    mean = statistics.mean(data['Regression'])
    return median, mean


if __name__ == '__main__':
    main()
