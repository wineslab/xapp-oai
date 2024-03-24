# (c) 2024 Northeastern University
# Institute for the Wireless Internet of Things
# Created by Davide Villa (villa.d@northeastern.edu)

# Test Influx dB capabilities and new features

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.query_api import QueryOptions
import datetime

def execute_query(query_api, bucket, start_time, end_time, field, n):
    """Build, execute InfluxDB query, and return result"""

    # Convert times to string in RFC3339 format, which is required by Flux
    start_time_str = start_time + "Z"
    end_time_str = end_time + "Z"

    # Build the query
    query_latest_points = f"""
                    from(bucket: "{bucket}")
                    |> range(start: {start_time_str}, stop: {end_time_str})
                    |> filter(fn: (r) => r._measurement == "xapp-stats" and r._field == "{field}")
                    |> group(columns: ["rnti"])
                    |> sort(columns: ["_time"], desc: true)
                    |> limit(n:{n})
                    """

    # Execute the quetry
    return query_api.query(query_latest_points)


def main():
    bucket = "wineslab-xapp-demo"
    client = InfluxDBClient.from_config_file("influx-db-config.ini")
    # print(client)
    query_api = client.query_api(query_options=QueryOptions())

    # Get start and end datetime
    start_time = datetime.datetime.now() - datetime.timedelta(seconds=3600)
    start_time = start_time.isoformat()
    end_time = datetime.datetime.now() + datetime.timedelta(seconds=100000) # Delta for timezones
    end_time = end_time.isoformat()

    # Execute queries to get slice for each rnti and downlink throughput info
    sst_data = execute_query(query_api, bucket, start_time, end_time, "nssai_sst", 1)
    sd_data = execute_query(query_api, bucket, start_time, end_time, "nssai_sd", 1)
    dlth_data = execute_query(query_api, bucket, start_time, end_time, "dl_th", 10)

    # Map RNTI with sst and sd
    rnti_slice_mapping = {}
    for sst_table in sst_data:
        for sst_record in sst_table:
            rnti = sst_record.values['rnti']
            sst = sst_record.values['_value']
            rnti_slice_mapping[rnti] = {'sst': sst}


    for sd_table in sd_data:
        for sd_record in sd_table:
            rnti = sd_record.values['rnti']
            sd = sd_record.values['_value']
            if rnti in rnti_slice_mapping:
                rnti_slice_mapping[rnti]['sd'] = sd

    # Map each slide with downlink throughput and compute average
    slice_dlth_mapping = {}
    for dlth_table in dlth_data:
        for dlth_record in dlth_table:
            rnti = dlth_record.values['rnti']
            dl_th = float(dlth_record.values['_value'])
            slice_id = (rnti_slice_mapping[rnti]['sst'], rnti_slice_mapping[rnti]['sd'])

            if slice_id not in slice_dlth_mapping:
                slice_dlth_mapping[slice_id] = {'total_dl_th': 0, 'count': 0}

            slice_dlth_mapping[slice_id]['total_dl_th'] += dl_th
            slice_dlth_mapping[slice_id]['count'] += 1

    for slice_id, data in slice_dlth_mapping.items():
        avg_dl_th = data['total_dl_th'] / data['count']
        slice_dlth_mapping[slice_id]['avg_dl_th'] = avg_dl_th

    print("RNTI to SST and SD Mapping:", rnti_slice_mapping)
    print("Average DL_TH for each slice:", slice_dlth_mapping)

    #for table in sst_data:
    #    for record in table.records:
    #        # Accessing the field name and value        
    #        print("RNTI: " + str(record['rnti']) + " - Field: " + str(record['_field']) + " - Value: " + str(record['_value']))

if __name__ == '__main__':
    main()
