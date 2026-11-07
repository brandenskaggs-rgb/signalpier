import unittest
from unittest.mock import patch
from spaceweather import SpaceWeather, latest


class WeatherTests(unittest.TestCase):
    def test_accepts_noaa_table_and_object_formats_and_sorts_timestamps(self):
        data=[['time_tag','Kp'],['2026-11-07 03:00:00','2.33'],['2026-11-07 00:00:00','3.00']]
        self.assertEqual(latest(data,'Kp')['value'],2.33)
        self.assertEqual(latest([{'time_tag':'2026-11-07T00:00:00','flux':125}],'flux')['value'],125)

    def test_invalid_data_is_unavailable_instead_of_fabricated(self):
        with self.assertRaises(ValueError): latest([{'time_tag':'bad','Kp':3}],'Kp')
        weather=SpaceWeather()
        with patch('spaceweather.urlopen',side_effect=OSError('offline')):
            data=weather.get()
        self.assertIsNone(data['kp']['value']);self.assertIn('offline',data['kp']['error'])

    def test_cache_avoids_repeated_requests(self):
        weather=SpaceWeather()
        def reading(name): return name,{'value':2,'observed_at':'2026-11-07T00:00:00Z','error':None}
        with patch.object(weather,'fetch_one',side_effect=reading) as fetch:
            first=weather.get();second=weather.get()
        self.assertIs(first,second);self.assertEqual(fetch.call_count,2)
