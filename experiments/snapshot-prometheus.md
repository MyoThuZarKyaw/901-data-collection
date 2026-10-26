## How to Backup?

1. Create snapshot inside prometheus container (no need to stop premetheus)

```shell

experiments git:(main) ✗ curl -XPOST http://localhost:9090/api/v1/admin/tsdb/snapshot
{"status":"success","data":{"name":"20261026T122143Z-13b0a6548d6ab701"}}%  

```

2. Copy the snapshot file from docker into my machine

```shell

docker cp prometheus:/prometheus/snapshots/20261026T122143Z-13b0a6548d6ab701 ./output/prometheus-snap-27OCT012300

```

## How to Restore?

???